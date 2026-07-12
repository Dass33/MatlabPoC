"""
Bridge to the compiled MATLAB nsm_algorithms package.

The MCR runs in a separate worker process (mcr_worker.py), started once on
first call and restarted if it dies. Keeping it out of the web server's
address space means a native fault in the MATLAB runtime stack (JVM, TBB,
its own libstdc++) costs one failed call, not the whole app - an in-process
MCR once segfaulted pyarrow and wedged the server (2026-07-12 incident).
All functions communicate via JSON strings.
"""

from __future__ import annotations

import json
import logging
import os
import select
import subprocess
import sys
import threading
from collections.abc import Mapping
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import numpy as np
from env import MCR_ROOT
from utils import to_json

_INIT_TIMEOUT_S = 300  # MCR cold start takes ~30s; leave slack for slow hosts
_CALL_TIMEOUT_S = 600


def _prep_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in collection.items():
        if isinstance(v, np.ndarray):
            out[k] = v.tolist()
        elif isinstance(v, (list, tuple)) and v and isinstance(v[0], np.ndarray):
            out[k] = [a.tolist() for a in v]
        else:
            out[k] = v
    return out


class Collection(TypedDict):
    iOC: np.ndarray
    STDiOC: np.ndarray
    N: np.ndarray
    D: np.ndarray
    velocity: np.ndarray
    positionRefined: np.ndarray
    timeFrame: np.ndarray
    iOCprofile: np.ndarray
    positionStart: NotRequired[np.ndarray]
    positionEnd: NotRequired[np.ndarray]
    ExperimentTimeStamp: NotRequired[np.ndarray]


class MatlabFilterSetting(TypedDict):
    filterProperties: list[str]
    thresholdDirection: list[str]
    thresholdValue: list[str | list[float]]
    referenceProperty: str


class PostprocessingResult(TypedDict):
    notOutlier: np.ndarray
    iOC: np.ndarray
    STDiOC: np.ndarray
    N: np.ndarray
    threshold: object
    calibration: dict[str, object] | None


log = logging.getLogger(__name__)


class _McrWorker:
    """Proxy for the nsm_algorithms package, backed by a worker subprocess.

    Exposes the same run* methods as the compiled package. Calls are
    serialised by a lock (the in-process MCR handled one call at a time too).
    """

    def __init__(self) -> None:
        rfd, wfd = os.pipe()
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = ":".join(
            f"{MCR_ROOT}/{p}"
            for p in (
                "runtime/glnxa64",
                "bin/glnxa64",
                "sys/os/glnxa64",
                "extern/bin/glnxa64",
            )
        )
        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-u",
                str(Path(__file__).with_name("mcr_worker.py")),
                str(wfd),
            ],
            stdin=subprocess.PIPE,
            pass_fds=(wfd,),
            env=env,
        )
        os.close(wfd)
        self._rfd = rfd
        self._rbuf = b""
        self._next_id = 0
        self._lock = threading.Lock()

        ready = self._read_response(_INIT_TIMEOUT_S)
        if not ready.get("ready"):
            self._kill()
            raise RuntimeError(
                f"MCR worker failed to start: {ready.get('error', ready)}"
            )
        log.info("MATLAB MCR initialised (worker pid=%s)", self._proc.pid)

    def alive(self) -> bool:
        return self._proc.poll() is None

    def _kill(self) -> None:
        self._proc.kill()
        self._proc.wait()
        os.close(self._rfd)

    def _read_response(self, timeout_s: float) -> dict:
        while b"\n" not in self._rbuf:
            r, _, _ = select.select([self._rfd], [], [], timeout_s)
            if not r:
                raise TimeoutError(f"no response from MCR worker in {timeout_s}s")
            chunk = os.read(self._rfd, 65536)
            if not chunk:
                raise RuntimeError(
                    f"MCR worker died (exit code {self._proc.poll()}); see logs"
                )
            self._rbuf += chunk
        line, self._rbuf = self._rbuf.split(b"\n", 1)
        return json.loads(line)

    def _call(self, fn: str, args: tuple[str, ...]) -> str:
        with self._lock:
            self._next_id += 1
            req = {"id": self._next_id, "fn": fn, "args": list(args)}
            try:
                stdin = self._proc.stdin
                assert stdin is not None
                stdin.write((json.dumps(req) + "\n").encode())
                stdin.flush()
                resp = self._read_response(_CALL_TIMEOUT_S)
            except (OSError, TimeoutError, RuntimeError) as e:
                self._kill()
                raise RuntimeError(f"MATLAB call {fn} failed: {e}") from e
            if "error" in resp:
                raise RuntimeError(f"MATLAB call {fn} failed:\n{resp['error']}")
            return resp["result"]

    def runOutlierFiltering(
        self, collection_json: str, setting_json: str, nargout: int = 1
    ) -> str:
        return self._call("runOutlierFiltering", (collection_json, setting_json))

    def runPostprocessing(
        self,
        collection_json: str,
        settings_json: str,
        keep_json: str,
        force_json: str,
        nargout: int = 1,
    ) -> str:
        return self._call(
            "runPostprocessing", (collection_json, settings_json, keep_json, force_json)
        )

    def runPopulationAnalysis(
        self, collection_json: str, setting_json: str, nargout: int = 1
    ) -> str:
        return self._call("runPopulationAnalysis", (collection_json, setting_json))


_pkg: _McrWorker | None = None
_pkg_lock = threading.Lock()


def _get_pkg() -> Any:
    global _pkg
    with _pkg_lock:
        if _pkg is None or not _pkg.alive():
            _pkg = _McrWorker()
    return _pkg


def warm_up() -> None:
    """Eagerly initialise the MCR so the first interactive call isn't slow.

    Intended to run in a background thread at app startup. Failures are logged,
    not raised — the next real call will retry lazily via _get_pkg().
    """
    try:
        _get_pkg()
    except Exception as e:  # MCR init surfaces various runtime/import errors
        log.warning("MCR warm-up failed (will retry on first call): %s", e)


def serialize_collection(collection: Mapping[str, Any]) -> str:
    """JSON-serialise a collection for the MATLAB bridge (numpy arrays → lists)."""
    return to_json(_prep_collection(collection))


def find_outliers(
    collection: Collection, matlab_setting: MatlabFilterSetting
) -> np.ndarray:
    """Returns a boolean mask of length N where True means the trajectory is not an outlier."""
    return find_outliers_json(serialize_collection(collection), to_json(matlab_setting))


def find_outliers_json(collection_json: str, setting_json: str) -> np.ndarray:
    """find_outliers on pre-serialised inputs. Separated so callers can cache on the
    JSON strings and skip the MCR round-trip on repeated identical inputs."""
    result = _get_pkg().runOutlierFiltering(
        collection_json,
        setting_json,
        nargout=1,
    )
    return np.array(json.loads(str(result)), dtype=bool)


def run_postprocessing(
    collection: Collection,
    matlab_setting: MatlabFilterSetting,
    keep_mask: np.ndarray,
    force_keep: np.ndarray,
    calibration_on: bool = True,
) -> PostprocessingResult:
    """Runs outlier filtering and optional iOC calibration via MATLAB. Returns a PostprocessingResult."""
    postprocessing_setting = {
        "iOCcalibration": "on" if calibration_on else "off",
        "outlierFiltering": matlab_setting,
    }
    preped_collection = to_json(_prep_collection(collection))
    settings_json = to_json(postprocessing_setting)
    keep_mask_json = to_json(keep_mask.tolist())
    force_keep_json = to_json(force_keep.tolist())

    result_json = _get_pkg().runPostprocessing(
        preped_collection,
        settings_json,
        keep_mask_json,
        force_keep_json,
        nargout=1,
    )
    data = json.loads(str(result_json))
    data["notOutlier"] = np.array(data["notOutlier"], dtype=bool)
    for key in ("iOC", "STDiOC", "N"):
        if key in data:
            data[key] = np.array(data[key], dtype=float)
    if not data.get("calibration"):
        data["calibration"] = None
    return data


def run_population_analysis(
    collection: dict[str, object], setting: dict[str, object]
) -> dict[str, object]:
    """Runs population analysis via MATLAB. Returns statistics keyed by property name (MEAN, STD, FWHM, RESOLUTION, histogram bins/counts)."""
    result_json = _get_pkg().runPopulationAnalysis(
        to_json(collection),
        to_json(setting),
        nargout=1,
    )
    return json.loads(str(result_json))

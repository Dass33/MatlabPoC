"""
Bridge to the compiled MATLAB nsm_algorithms package.

MCR is initialised once per process on first call.
All functions communicate via JSON strings.
"""

from __future__ import annotations

import importlib
import json
import logging
import threading
from collections.abc import Mapping
from typing import Any, NotRequired, TypedDict

import numpy as np
from utils import to_json

_MCR_PACKAGE = "nsm_algorithms"  # installed at matlab/Compiled/PythonPackage


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

_pkg = None
_pkg_lock = threading.Lock()


def _get_pkg() -> Any:
    global _pkg
    if _pkg is None:
        with _pkg_lock:
            if _pkg is None:
                _pkg = importlib.import_module(_MCR_PACKAGE).initialize()
                log.info("MATLAB MCR initialised")
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

import importlib
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))

STREAMLIT_DIR = Path(__file__).parent.parent / "streamlit"
REPO_ROOT = Path(__file__).parent.parent
SYNTH_TIFF_DIR = REPO_ROOT / "matlab" / "nsm-data-analysis" / "syntheticDataCreation" / "output" / "tiff_kymographs"

# A known-good TIFF pair from the submodule (iOC=0.002, velocity=15, D=5)
FIXTURE_STEM = "iOC0.002_velocity15_D5_conc1_1"
# A TIFF pair that is known to cause iOC calibration to fail
FIXTURE_STEM_CAL_FAIL = "iOC0.0008_velocity15_D5_conc2_1"


def pytest_addoption(parser):
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests that require Docker + matlab-algorithm:latest",
    )
    parser.addoption(
        "--ai-review",
        action="store_true",
        default=False,
        help="Run AI review of output figures via Claude Code after integration tests",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: requires Docker + matlab-algorithm:latest image",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="pass --run-integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip)


# ── Helpers ───────────────────────────────────────────────────────────────────


class MockFile:
    """Minimal stand-in for Streamlit UploadedFile."""
    def __init__(self, name: str, content: bytes):
        self.name = name
        self._buf = BytesIO(content)

    def read(self, size: int = -1) -> bytes:
        return self._buf.read(size)

    def seek(self, pos: int) -> None:
        self._buf.seek(pos)


def _load_job_manager(data_dir: Path):
    os.environ["DATA_DIR"] = str(data_dir)
    os.environ["HOST_DATA_DIR"] = str(data_dir)
    import job_manager
    importlib.reload(job_manager)
    return job_manager


def _poll_until_done(jm, job_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        status = jm.read_status(job_id)
        if status["status"] != "processing":
            return status
        time.sleep(5)
    raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")


def _tiff_pair(stem: str) -> list[MockFile]:
    return [
        MockFile(f"{stem}.tiff", (SYNTH_TIFF_DIR / f"{stem}.tiff").read_bytes()),
        MockFile(f"{stem}.txt",  (SYNTH_TIFF_DIR / f"{stem}.txt").read_bytes()),
    ]


# ── Integration fixtures ──────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def completed_job(tmp_path_factory):
    """Submits a real job and waits for completion. Shared across the session."""
    from config import DEFAULT_CONFIG

    data_dir = tmp_path_factory.mktemp("jobs")
    jm = _load_job_manager(data_dir)

    job_id = jm.submit_job(_tiff_pair(FIXTURE_STEM), DEFAULT_CONFIG)
    status = _poll_until_done(jm, job_id)

    return {
        "job_id": job_id,
        "data_dir": data_dir,
        "status": status,
        "jm": jm,
    }


@pytest.fixture(scope="session")
def completed_job_cal_fail(tmp_path_factory):
    """Job using the TIFF that causes iOC calibration to fail."""
    from config import DEFAULT_CONFIG

    data_dir = tmp_path_factory.mktemp("jobs_cal_fail")
    jm = _load_job_manager(data_dir)

    job_id = jm.submit_job(_tiff_pair(FIXTURE_STEM_CAL_FAIL), DEFAULT_CONFIG)
    status = _poll_until_done(jm, job_id)

    return {
        "job_id": job_id,
        "data_dir": data_dir,
        "status": status,
        "jm": jm,
    }


@pytest.fixture(scope="session")
def postprocessed_job(completed_job):
    """Runs postprocessing (all tracks kept, no calibration) on the completed job."""
    import numpy as np
    import scipy.io

    job_id = completed_job["job_id"]
    data_dir = completed_job["data_dir"]
    jm = completed_job["jm"]

    _, _, out = jm.job_dirs(job_id)
    mat_path = out / "collection" / "collection.mat"

    m = scipy.io.loadmat(str(mat_path), squeeze_me=True)
    c = m["collection"]
    collection = {f: c[f].item() for f in c.dtype.names}

    pos = collection.get("positionRefined")
    if pos is not None:
        collection["positionStart"] = np.array([float(p.min()) for p in pos])
        collection["positionEnd"] = np.array([float(p.max()) for p in pos])

    n = len(collection["iOC"])
    keep_mask = np.ones(n, dtype=bool)

    def _default(obj):
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        raise TypeError(type(obj))

    def _filter(col, mask):
        result = {}
        for k, v in col.items():
            if isinstance(v, np.ndarray) and len(v) == len(mask):
                result[k] = v[mask].tolist()
            elif isinstance(v, (list, tuple)) and len(v) == len(mask):
                result[k] = [v[i] for i, m in enumerate(mask) if m]
        return result

    (out / "collection_postprocessed.json").write_text(
        json.dumps({
            "collection": _filter(collection, keep_mask),
            "calibration": None,
            "n_kept": int(keep_mask.sum()),
            "n_total": n,
        }, indent=2, default=_default)
    )

    return {**completed_job, "collection": collection, "n_total": n}

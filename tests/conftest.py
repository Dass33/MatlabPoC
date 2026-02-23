"""Global pytest configuration: sys.path, mocks, and shared fixtures."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
import scipy.io

# DATA_DIR must point somewhere writable before job_manager is imported,
# because that module calls DATA_DIR.mkdir() at import time.
_tmp_root = tempfile.mkdtemp(prefix="nsm_test_")
os.environ.setdefault("DATA_DIR", _tmp_root)
os.environ.setdefault("HOST_DATA_DIR", _tmp_root)

# Mock external packages before any project module is imported.
sys.modules["streamlit"] = MagicMock()
sys.modules["docker"] = MagicMock()

# Expose the Streamlit source directory so project modules are importable
# as top-level names (e.g. `from config import ...`).
_SRC = Path(__file__).parent.parent / "streamlit"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))


# ── pytest CLI options (used by integration tests) ────────────────────────────

def pytest_addoption(parser):
    parser.addoption(
        "--run-integration", action="store_true", default=False,
        help="Run integration tests (requires matlab-algorithm:latest Docker image)",
    )
    parser.addoption(
        "--update-golden", action="store_true", default=False,
        help="Overwrite golden reference values after a successful integration run",
    )
    parser.addoption(
        "--check-golden", action="store_true", default=False,
        help="Compare integration outputs against golden reference values",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-integration"):
        skip = pytest.mark.skip(reason="pass --run-integration to enable")
        for item in items:
            if item.get_closest_marker("integration"):
                item.add_marker(skip)


# ── Shared fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """Redirect job_manager.DATA_DIR to an isolated tmp_path for the test."""
    import job_manager
    monkeypatch.setattr(job_manager, "DATA_DIR", tmp_path)
    return tmp_path


@pytest.fixture
def job_dir(data_dir):
    """One job directory (input/ + output/ + meta.json) under data_dir."""
    job_id = "20240101_120000_abc123"
    base = data_dir / job_id
    (base / "input").mkdir(parents=True)
    (base / "output").mkdir(parents=True)
    (base / "meta.json").write_text(
        '{"job_id": "20240101_120000_abc123", '
        '"filenames": ["test.tiff"], '
        '"submitted_at": "2024-01-01T12:00:00"}'
    )
    return job_id, base


@pytest.fixture
def mat_fixture(tmp_path):
    """A minimal trajectories.mat that load_trajectories() can parse.

    sweepLegends is stored as a 2-D object array containing a char array per
    cell, mirroring how scipy.io.loadmat reconstructs MATLAB cell arrays of
    char vectors: each cell element is a 1-element numpy array.
    """
    n = 10

    legends = np.empty((1, 1), dtype=object)
    legends[0, 0] = np.array(["Wx=10,Wt=30"])

    data = {
        "iOC":           np.ones(n, dtype=float),
        "D":             np.full(n, 0.5, dtype=float),
        "velocity":      np.full(n, -3.4, dtype=float),
        "N":             np.full(n, 20.0, dtype=float),
        "positionStart": np.zeros(n, dtype=float),
        "positionEnd":   np.full(n, 100.0, dtype=float),
        "sweepIdx":      np.ones(n, dtype=float),
        "sweepLegends":  legends,
    }
    p = tmp_path / "trajectories.mat"
    scipy.io.savemat(str(p), data)
    return p

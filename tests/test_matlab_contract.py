"""Contract tests against the REAL compiled MATLAB bridge.

Unlike test_algorithms.py (which mocks _get_pkg and only proves our own
serialize/parse round-trips), these call the actual nsm_algorithms MCR package
to verify the JSON contract our Python code assumes matches what MATLAB expects.

They are skipped automatically unless the runtime is present, so they are inert
on a dev machine without MATLAB and only exercise the boundary in the Docker/CI
image that ships the MCR. Run there with:  pytest -m integration
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from env import MCR_ROOT

# The MCR now runs in a worker subprocess which sets LD_LIBRARY_PATH for
# itself, so this process must not import nsm_algorithms - just check that
# the package and the runtime are present.
if importlib.util.find_spec("nsm_algorithms") is None or not Path(MCR_ROOT).is_dir():
    pytest.skip(
        "compiled MATLAB runtime unavailable; "
        "needs the nsm_algorithms package on PYTHONPATH and the R2025b runtime",
        allow_module_level=True,
    )

from connectors import algorithms  # noqa: E402
from sample_data import sample_collection  # noqa: E402

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mcr():
    try:
        algorithms._get_pkg()
    except Exception as e:  # MCR present but fails to initialise
        pytest.skip(f"MCR unavailable: {e}")
    return algorithms


def _sample_setting() -> dict:
    return {
        "filterProperties": ["iOC", "D"],
        "thresholdDirection": ["both", "both"],
        "thresholdValue": ["3std", "3std"],
        "referenceProperty": "iOC",
    }


def test_find_outliers_returns_bool_mask_of_matching_length(mcr):
    collection = sample_collection(8)
    mask = mcr.find_outliers(collection, _sample_setting())  # type: ignore[arg-type]
    assert mask.dtype == bool
    assert mask.shape == (8,)


def test_run_postprocessing_returns_expected_keys(mcr):
    collection = sample_collection(8)
    result = mcr.run_postprocessing(
        collection,  # type: ignore[arg-type]
        _sample_setting(),  # type: ignore[arg-type]
        keep_mask=np.ones(8, dtype=bool),
        force_keep=np.zeros(8, dtype=bool),
        calibration_on=True,
    )
    assert result["notOutlier"].dtype == bool
    assert result["notOutlier"].shape == (8,)
    assert "calibration" in result

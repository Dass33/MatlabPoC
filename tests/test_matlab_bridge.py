"""
Unit tests for matlab_bridge.py
Tests serialization helpers and API contracts (mocked MATLAB calls).
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))


# ── Serialisation helpers ───────────────────────────────────────────────────────


def test_to_json_with_ndarray():
    from matlab_bridge import _to_json

    arr = np.array([1, 2, 3])
    result = _to_json({"data": arr})
    assert '"data": [1, 2, 3]' in result


def test_to_json_with_ndarray_2d():
    from matlab_bridge import _to_json

    arr = np.array([[1, 2], [3, 4]])
    result = _to_json({"data": arr})
    assert '"data": [[1, 2], [3, 4]]' in result


def test_to_json_with_np_integer():
    from matlab_bridge import _to_json

    val = np.int64(42)
    result = _to_json({"data": val})
    assert '"data": 42' in result


def test_to_json_with_np_floating():
    from matlab_bridge import _to_json

    val = np.float64(3.14)
    result = _to_json({"data": val})
    assert '"data": 3.14' in result


def test_to_json_raises_on_unknown():
    from matlab_bridge import _to_json

    class UnknownType:
        pass

    with pytest.raises(TypeError):
        _to_json({"data": UnknownType()})


def test_from_json_basic():
    from matlab_bridge import _from_json

    result = _from_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_from_json_with_arrays():
    from matlab_bridge import _from_json

    result = _from_json('{"data": [1, 2, 3]}')
    assert result["data"] == [1, 2, 3]


# ── Collection preparation ─────────────────────────────────────────────────


def test_prep_collection_with_ndarray():
    from matlab_bridge import _prep_collection

    collection = {"iOC": np.array([1.0, 2.0, 3.0])}
    result = _prep_collection(collection)

    assert result["iOC"] == [1.0, 2.0, 3.0]
    assert isinstance(result["iOC"], list)


def test_prep_collection_with_nested_arrays():
    from matlab_bridge import _prep_collection

    collection = {
        "iOCprofile": [np.array([1.0, 2.0]), np.array([3.0, 4.0])]
    }
    result = _prep_collection(collection)

    assert result["iOCprofile"] == [[1.0, 2.0], [3.0, 4.0]]


def test_prep_collection_mixed():
    from matlab_bridge import _prep_collection

    collection = {
        "iOC": np.array([1.0, 2.0]),
        "N": 42,
        "name": "test",
    }
    result = _prep_collection(collection)

    assert result["iOC"] == [1.0, 2.0]
    assert result["N"] == 42
    assert result["name"] == "test"


def test_prep_collection_no_arrays():
    from matlab_bridge import _prep_collection

    collection = {"N": 42, "name": "test"}
    result = _prep_collection(collection)

    assert result == {"N": 42, "name": "test"}


# ── find_outliers API contract ──────────────────────────────────────────


def test_find_outliers_returns_bool_array():
    from matlab_bridge import find_outliers

    collection = {
        "iOC": np.array([1e-6, 2e-6, 3e-6]),
        "STDiOC": np.array([1e-7, 2e-7, 3e-7]),
        "velocity": np.array([10.0, 15.0, 20.0]),
        "N": np.array([100, 200, 300]),
    }
    matlab_setting = {
        "filterProperties": ["STDiOC"],
        "thresholdDirection": ["upper"],
        "thresholdValue": ["3std"],
    }

    mock_pkg = MagicMock()
    mock_pkg.runOutlierFiltering.return_value = '[true, true, false]'

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        result = find_outliers(collection, matlab_setting)

    assert isinstance(result, np.ndarray)
    assert result.dtype == bool
    assert len(result) == 3


def test_find_outliers_passes_correct_json():
    from matlab_bridge import find_outliers, _to_json

    collection = {"iOC": np.array([1.0])}
    matlab_setting = {"filterProperties": ["STDiOC"], "thresholdDirection": ["upper"], "thresholdValue": ["3std"]}

    captured_args = {}

    def capture(*args, **kwargs):
        captured_args["collection"] = args[0]
        captured_args["setting"] = args[1]
        return "[true]"

    mock_pkg = MagicMock()
    mock_pkg.runOutlierFiltering.side_effect = capture

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        with patch("matlab_bridge._to_json", side_effect=lambda x: _to_json(x)) as mock_json:
            find_outliers(collection, matlab_setting)

    assert "collection" in captured_args
    assert "filterProperties" in captured_args["setting"]


# ── run_postprocessing API contract ───────────────────────────────────────


def test_run_postprocessing_returns_dict():
    from matlab_bridge import run_postprocessing

    collection = {"iOC": np.array([1e-6, 2e-6, 3e-6])}
    matlab_setting = {
        "filterProperties": ["STDiOC"],
        "thresholdDirection": ["upper"],
        "thresholdValue": ["3std"],
    }
    keep_mask = np.array([True, True, True])

    mock_result = {
        "notOutlier": [True, True, True],
        "iOC": [1e-6, 2e-6, 3e-6],
        "STDiOC": [1e-7, 2e-7, 3e-7],
        "N": [100, 200, 300],
        "threshold": {},
        "calibration": None,
    }

    mock_pkg = MagicMock()
    mock_pkg.runPostprocessing.return_value = json.dumps(mock_result)

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        result = run_postprocessing(collection, matlab_setting, keep_mask, calibration_on=False)

    assert isinstance(result, dict)
    assert "notOutlier" in result
    assert "iOC" in result


def test_run_postprocessing_calibration_off():
    from matlab_bridge import run_postprocessing, _to_json

    collection = {"iOC": np.array([1.0])}
    matlab_setting = {"filterProperties": [], "thresholdDirection": [], "thresholdValue": []}
    keep_mask = np.array([True])

    mock_pkg = MagicMock()
    mock_pkg.runPostprocessing.return_value = '{"notOutlier": [true], "calibration": null}'

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        result = run_postprocessing(collection, matlab_setting, keep_mask, calibration_on=False)

    assert result["calibration"] is None


# ── run_population_analysis API contract ───────────────────────────────────


def test_run_population_analysis_returns_dict():
    from matlab_bridge import run_population_analysis

    collection = {"iOC": [1e-6, 2e-6]}
    setting = {"Title": "robustMean", "properties": ["iOC"]}

    mock_result = {
        "iOC": {
            "MEAN": 1.5e-6,
            "STD": 0.5e-6,
            "FWHM": 1.0e-6,
            "RESOLUTION": 1.0e-7,
        }
    }

    mock_pkg = MagicMock()
    mock_pkg.runPopulationAnalysis.return_value = json.dumps(mock_result)

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        result = run_population_analysis(collection, setting)

    assert isinstance(result, dict)
    assert "iOC" in result
    assert result["iOC"]["MEAN"] == 1.5e-6


def test_run_population_analysis_renames_histogram_fields():
    from matlab_bridge import run_population_analysis

    collection = {"iOC": [1e-6]}
    setting = {"Title": "gaussFit", "properties": ["iOC"]}

    mock_result = {
        "iOC": {
            "MEAN": 1e-6,
            "STD": 0.5e-6,
            "histCenters": [1e-6, 1.1e-6],
            "histCounts": [10, 20],
        }
    }

    mock_pkg = MagicMock()
    mock_pkg.runPopulationAnalysis.return_value = json.dumps(mock_result)

    with patch("matlab_bridge._get_pkg", return_value=mock_pkg):
        result = run_population_analysis(collection, setting)

    assert "_hist_centers" in result["iOC"]
    assert "_hist_counts" in result["iOC"]
    assert "histCenters" not in result["iOC"]
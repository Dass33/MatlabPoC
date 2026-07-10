from __future__ import annotations

import json

import numpy as np
import pytest

from connectors import algorithms


class FakePkg:
    """Stand-in for the compiled nsm_algorithms MCR package.

    Records the JSON strings it receives and returns canned JSON, so the real
    serialize/parse logic in algorithms.py is exercised without MATLAB.
    """

    def __init__(self, outlier=None, postprocessing=None, population=None):
        self.calls: dict[str, tuple] = {}
        self._outlier = outlier
        self._postprocessing = postprocessing
        self._population = population

    def runOutlierFiltering(self, collection_json, setting_json, nargout=1):
        self.calls["outlier"] = (collection_json, setting_json)
        return json.dumps(self._outlier)

    def runPostprocessing(self, collection_json, settings_json, keep_json, force_json, nargout=1):
        self.calls["postprocessing"] = (collection_json, settings_json, keep_json, force_json)
        return json.dumps(self._postprocessing)

    def runPopulationAnalysis(self, collection_json, setting_json, nargout=1):
        self.calls["population"] = (collection_json, setting_json)
        return json.dumps(self._population)


@pytest.fixture
def patch_pkg(monkeypatch):
    def _install(pkg):
        monkeypatch.setattr(algorithms, "_get_pkg", lambda: pkg)
        return pkg

    return _install


def test_prep_collection_converts_numpy():
    out = algorithms._prep_collection(
        {"a": np.array([1, 2]), "b": [np.array([1.0]), np.array([2.0])], "c": "x"}
    )
    assert out == {"a": [1, 2], "b": [[1.0], [2.0]], "c": "x"}


def test_find_outliers_serializes_inputs_and_parses_bool_mask(patch_pkg):
    pkg = patch_pkg(FakePkg(outlier=[True, False, True]))
    collection = {"iOC": np.array([1.0, 2.0, 3.0])}
    setting = {"filterProperties": ["iOC"], "thresholdDirection": ["both"],
               "thresholdValue": ["3std"], "referenceProperty": "iOC"}
    mask = algorithms.find_outliers(collection, setting)  # type: ignore[arg-type]

    assert mask.dtype == bool
    assert mask.tolist() == [True, False, True]
    # collection was serialized with numpy arrays flattened to lists
    assert json.loads(pkg.calls["outlier"][0]) == {"iOC": [1.0, 2.0, 3.0]}


def test_run_postprocessing_maps_calibration_flag_and_types(patch_pkg):
    pkg = patch_pkg(FakePkg(postprocessing={
        "notOutlier": [1, 0, 1],
        "iOC": [1.0, 2.0, 3.0],
        "N": [4, 5, 6],
        "calibration": {},
    }))
    collection = {"iOC": np.array([1.0, 2.0, 3.0])}
    setting = {"filterProperties": ["iOC"], "thresholdDirection": ["both"],
               "thresholdValue": ["3std"], "referenceProperty": "iOC"}

    result = algorithms.run_postprocessing(
        collection, setting,  # type: ignore[arg-type]
        keep_mask=np.array([True, True, True]),
        force_keep=np.array([False, False, False]),
        calibration_on=False,
    )

    settings_sent = json.loads(pkg.calls["postprocessing"][1])
    assert settings_sent["iOCcalibration"] == "off"
    assert result["notOutlier"].dtype == bool
    assert result["iOC"].dtype == float
    # empty calibration dict is normalized to None
    assert result["calibration"] is None


def test_run_postprocessing_calibration_on(patch_pkg):
    pkg = patch_pkg(FakePkg(postprocessing={"notOutlier": [1], "calibration": {"slope": 2.0}}))
    algorithms.run_postprocessing(
        {"iOC": np.array([1.0])}, {},  # type: ignore[arg-type]
        keep_mask=np.array([True]), force_keep=np.array([False]),
        calibration_on=True,
    )
    assert json.loads(pkg.calls["postprocessing"][1])["iOCcalibration"] == "on"


def test_run_population_analysis_passthrough(patch_pkg):
    patch_pkg(FakePkg(population={"iOC": {"MEAN": 1.5, "FWHM": 0.3}}))
    stats = algorithms.run_population_analysis({"iOC": [1.0, 2.0]}, {"bins": 10})
    assert stats == {"iOC": {"MEAN": 1.5, "FWHM": 0.3}}


def test_warm_up_swallows_init_errors(monkeypatch):
    def boom():
        raise RuntimeError("MCR unavailable")

    monkeypatch.setattr(algorithms, "_get_pkg", boom)
    algorithms.warm_up()  # must not raise

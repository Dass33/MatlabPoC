"""Unit tests for streamlit/config.py."""
from __future__ import annotations

import streamlit as st

from config import DEFAULT_CONFIG, _build_config, _parse_sweep_values

_REQUIRED_TOP_LEVEL = [
    "Dt", "Dx", "flipIntensity", "flowEstimate",
    "kymographPreprocessing", "Detection", "Linking",
    "trajectoryProperties", "iOCcalibration", "outlierFiltering",
    "populationAnalysis",
]

_BUILD_DEFAULTS = dict(
    Dt=0.007, Dx=0.066, flipIntensity=True, flowEstimate=-3.4,
    darkCalibration=8, Wx=15.0, Wt=50.0, ws=2.36,
    peakSign="negative", pfa=1e-5, localOptimumRange=6,
    minTrackLength=10, cut_off_distance=20.0, unmatched_penalty_distance=15.0,
    maxNegativeGab=2, maxPositiveGab=3,
    gab_closing_cut_off_distance=40.0, gab_closing_penalty_distance=30.0,
    iOCcalibration="on", pop_method="robustMean",
)


def _build(**overrides):
    return _build_config(**{**_BUILD_DEFAULTS, **overrides})


class TestParseSweepValues:
    def test_single_value(self):
        assert _parse_sweep_values("15.0") == [15.0]

    def test_multiple_values(self):
        assert _parse_sweep_values("10, 20.0, 30") == [10.0, 20.0, 30.0]

    def test_bad_string_warns_and_returns_default(self, mocker):
        mock_warn = mocker.patch("streamlit.warning")
        result = _parse_sweep_values("abc,1.0")
        assert result == [15.0]
        mock_warn.assert_called_once()

    def test_empty_string_returns_empty_list(self):
        assert _parse_sweep_values("") == []


class TestBuildConfig:
    def test_has_all_required_top_level_keys(self):
        cfg = _build()
        for key in _REQUIRED_TOP_LEVEL:
            assert key in cfg, f"Missing required key: {key}"

    def test_dark_calibration_coerced_to_int(self):
        cfg = _build(darkCalibration=8.9)
        assert isinstance(cfg["kymographPreprocessing"]["darkCalibration"], int)

    def test_pfa_coerced_to_float(self):
        cfg = _build(pfa=1e-5)
        assert isinstance(cfg["Detection"]["pfa"], float)

    def test_local_optimum_range_coerced_to_int(self):
        cfg = _build(localOptimumRange=6)
        assert isinstance(cfg["Detection"]["localOptimumRange"], int)

    def test_min_track_length_coerced_to_int(self):
        cfg = _build(minTrackLength=10)
        assert isinstance(cfg["Linking"]["minTrackLength"], int)

    def test_scalar_wx_stays_float(self):
        cfg = _build(Wx=10.0)
        assert isinstance(cfg["kymographPreprocessing"]["Wx"], float)

    def test_list_wx_passed_through_unchanged(self):
        cfg = _build(Wx=[10.0, 15.0])
        assert cfg["kymographPreprocessing"]["Wx"] == [10.0, 15.0]

    def test_list_wt_passed_through_unchanged(self):
        cfg = _build(Wt=[30.0, 50.0])
        assert cfg["kymographPreprocessing"]["Wt"] == [30.0, 50.0]

    def test_ioc_calibration_off_passthrough(self):
        cfg = _build(iOCcalibration="off")
        assert cfg["iOCcalibration"] == "off"

    def test_pop_method_stored_in_population_analysis(self):
        cfg = _build(pop_method="GMM")
        assert cfg["populationAnalysis"]["Title"] == "GMM"


class TestDefaultConfig:
    def test_has_all_required_top_level_keys(self):
        for key in _REQUIRED_TOP_LEVEL:
            assert key in DEFAULT_CONFIG, f"Missing key: {key}"

    def test_dt_is_float(self):
        assert isinstance(DEFAULT_CONFIG["Dt"], float)

    def test_dx_is_float(self):
        assert isinstance(DEFAULT_CONFIG["Dx"], float)

    def test_pfa_is_float(self):
        assert isinstance(DEFAULT_CONFIG["Detection"]["pfa"], float)

    def test_flow_estimate_is_float(self):
        assert isinstance(DEFAULT_CONFIG["flowEstimate"], float)

    def test_trajectory_properties_is_list(self):
        assert isinstance(DEFAULT_CONFIG["trajectoryProperties"], list)
        assert len(DEFAULT_CONFIG["trajectoryProperties"]) > 0

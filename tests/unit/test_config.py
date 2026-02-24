"""Unit tests for streamlit/config.py."""
from __future__ import annotations

import pytest
import streamlit as st

from config import DEFAULT_CONFIG, _apply_config_to_session_state, _build_config, _parse_sweep_values

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
    tracker="gabClosingTracker",
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

    def test_tracker_defaults_to_gab_closing(self):
        cfg = _build()
        assert cfg["tracker"] == "gabClosingTracker"

    def test_tracker_track_before_detect(self):
        cfg = _build(tracker="trackBeforeDetect")
        assert cfg["tracker"] == "trackBeforeDetect"


class TestApplyConfigToSessionState:
    @pytest.fixture(autouse=True)
    def session_state(self, monkeypatch):
        state = {}
        monkeypatch.setattr(st, "session_state", state)
        self._state = state
        return state

    def test_flat_acquisition_fields(self):
        _apply_config_to_session_state({"Dt": 0.01, "Dx": 0.05, "flipIntensity": False, "flowEstimate": 1.0})
        assert self._state["Dt"] == 0.01
        assert self._state["Dx"] == 0.05
        assert self._state["flipIntensity"] is False
        assert self._state["flowEstimate"] == 1.0

    def test_preprocessing_scalar(self):
        _apply_config_to_session_state({"kymographPreprocessing": {"darkCalibration": 10, "Wx": 20.0, "Wt": 60.0, "ws": 3.0}})
        assert self._state["darkCalibration"] == 10
        assert self._state["ws"] == 3.0
        assert self._state["Wx_single"] == 20.0
        assert self._state["Wt_single"] == 60.0
        assert "sweep_enabled" not in self._state

    def test_preprocessing_sweep_wx(self):
        _apply_config_to_session_state({"kymographPreprocessing": {"Wx": [10.0, 20.0], "Wt": 50.0}})
        assert self._state["sweep_enabled"] is True
        assert self._state["Wx_sweep"] == "10.0, 20.0"
        assert self._state["Wt_single"] == 50.0

    def test_preprocessing_sweep_wt(self):
        _apply_config_to_session_state({"kymographPreprocessing": {"Wx": 15.0, "Wt": [30.0, 50.0, 70.0]}})
        assert self._state["sweep_enabled"] is True
        assert self._state["Wt_sweep"] == "30.0, 50.0, 70.0"
        assert self._state["Wx_single"] == 15.0

    def test_detection_fields(self):
        _apply_config_to_session_state({"Detection": {"peakSign": "positive", "pfa": 1e-4, "localOptimumRange": 8}})
        assert self._state["peakSign"] == "positive"
        assert self._state["pfa"] == 1e-4
        assert self._state["localOptimumRange"] == 8

    def test_linking_fields(self):
        link = {"minTrackLength": 5, "cut_off_distance": 25.0, "unmatched_penalty_distance": 10.0,
                "maxNegativeGab": 1, "maxPositiveGab": 4,
                "gab_closing_cut_off_distance": 35.0, "gab_closing_penalty_distance": 25.0}
        _apply_config_to_session_state({"Linking": link})
        for k, v in link.items():
            assert self._state[k] == v

    def test_ioc_calibration_on(self):
        _apply_config_to_session_state({"iOCcalibration": "on"})
        assert self._state["iOCcalibration_toggle"] is True

    def test_ioc_calibration_off(self):
        _apply_config_to_session_state({"iOCcalibration": "off"})
        assert self._state["iOCcalibration_toggle"] is False

    def test_population_analysis_title(self):
        _apply_config_to_session_state({"populationAnalysis": {"Title": "GMM"}})
        assert self._state["pop_method"] == "GMM"

    def test_tracker_loaded_into_session_state(self):
        _apply_config_to_session_state({"tracker": "trackBeforeDetect"})
        assert self._state["tracker"] == "trackBeforeDetect"

    def test_tracker_defaults_absent_when_not_in_config(self):
        _apply_config_to_session_state({"Dt": 0.007})
        assert "tracker" not in self._state

    def test_missing_fields_skipped(self):
        _apply_config_to_session_state({"Dt": 0.007})
        assert list(self._state.keys()) == ["Dt"]

    def test_roundtrip_from_build_config(self):
        exported = _build(**_BUILD_DEFAULTS)
        _apply_config_to_session_state(exported)
        assert self._state["Dt"] == _BUILD_DEFAULTS["Dt"]
        assert self._state["Dx"] == _BUILD_DEFAULTS["Dx"]
        assert self._state["Wx_single"] == float(_BUILD_DEFAULTS["Wx"])
        assert self._state["Wt_single"] == float(_BUILD_DEFAULTS["Wt"])
        assert self._state["pfa"] == _BUILD_DEFAULTS["pfa"]
        assert self._state["minTrackLength"] == _BUILD_DEFAULTS["minTrackLength"]
        assert self._state["iOCcalibration_toggle"] is True
        assert self._state["pop_method"] == _BUILD_DEFAULTS["pop_method"]
        assert self._state["tracker"] == _BUILD_DEFAULTS["tracker"]


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

    def test_default_tracker_is_gab_closing(self):
        assert DEFAULT_CONFIG["tracker"] == "gabClosingTracker"

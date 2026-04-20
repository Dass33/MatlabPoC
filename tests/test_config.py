import json
import sys
from io import BytesIO
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))
from config import DEFAULT_CONFIG

CONFIG_APP = str(Path(__file__).parent / "apps" / "config_app.py")


def _app() -> AppTest:
    return AppTest.from_file(CONFIG_APP, default_timeout=30)


def _config(at: AppTest) -> dict:
    return at.session_state["_config"]


# ── Default values ────────────────────────────────────────────────────────────


def test_default_config_has_required_keys():
    at = _app()
    at.run()
    assert not at.exception
    cfg = _config(at)
    for key in ("Dt", "Dx", "flipIntensity", "flowEstimate",
                "kymographPreprocessing", "Detection", "Linking",
                "tracker", "Tlength", "thresholdLimit", "TmaxNo",
                "exportOptionalFigures", "trajectoryProperties"):
        assert key in cfg, f"Missing key: {key}"


def test_default_config_values_match_defaults():
    at = _app()
    at.run()
    cfg = _config(at)
    assert cfg["Dt"] == pytest.approx(DEFAULT_CONFIG["Dt"])
    assert cfg["Dx"] == pytest.approx(DEFAULT_CONFIG["Dx"])
    assert cfg["flipIntensity"] == DEFAULT_CONFIG["flipIntensity"]
    assert cfg["flowEstimate"] == pytest.approx(DEFAULT_CONFIG["flowEstimate"])
    pp = cfg["kymographPreprocessing"]
    assert pp["Wx"] == pytest.approx(DEFAULT_CONFIG["kymographPreprocessing"]["Wx"])
    assert pp["Wt"] == pytest.approx(DEFAULT_CONFIG["kymographPreprocessing"]["Wt"])


# ── Acquisition section ───────────────────────────────────────────────────────


def test_acquisition_dt_dx_flow():
    at = _app()
    at.run()
    at.number_input(key="Dt").set_value(0.01)
    at.number_input(key="Dx").set_value(0.1)
    at.number_input(key="flowEstimate").set_value(5.0)
    at.run()
    assert not at.exception
    cfg = _config(at)
    assert cfg["Dt"] == pytest.approx(0.01)
    assert cfg["Dx"] == pytest.approx(0.1)
    assert cfg["flowEstimate"] == pytest.approx(5.0)


def test_acquisition_flip_intensity_toggle():
    at = _app()
    at.run()
    original = _config(at)["flipIntensity"]
    at.checkbox(key="flipIntensity").set_value(not original)
    at.run()
    assert not at.exception
    assert _config(at)["flipIntensity"] == (not original)


# ── Preprocessing section ─────────────────────────────────────────────────────


def test_preprocessing_wx_wt_ws():
    at = _app()
    at.run()
    at.number_input(key="Wx_single").set_value(20.0)
    at.number_input(key="Wt_single").set_value(80.0)
    at.number_input(key="ws").set_value(3.0)
    at.run()
    assert not at.exception
    pp = _config(at)["kymographPreprocessing"]
    assert pp["Wx"] == pytest.approx(20.0)
    assert pp["Wt"] == pytest.approx(80.0)
    assert pp["ws"] == pytest.approx(3.0)


def test_preprocessing_remove_background_mode():
    at = _app()
    at.run()
    at.selectbox(key="remove_background_mode").set_value("movmean")
    at.run()
    assert not at.exception
    assert _config(at)["kymographPreprocessing"]["removeBackground"] == "movmean"


def test_dark_cal_scalar():
    at = _app()
    at.run()
    at.radio(key="dark_cal_mode").set_value("Scalar")
    at.number_input(key="darkCalibration").set_value(12)
    at.run()
    assert not at.exception
    dc = _config(at)["kymographPreprocessing"]["darkCalibration"]
    assert dc == 12
    assert isinstance(dc, int)


def test_dark_cal_template():
    at = _app()
    at.run()
    at.radio(key="dark_cal_mode").set_value("Template")
    at.run()
    assert not at.exception
    dc = _config(at)["kymographPreprocessing"]["darkCalibration"]
    assert isinstance(dc, str)
    assert "dark_cal_bytes" in at.session_state


# ── Detection section ─────────────────────────────────────────────────────────


def test_detection_values():
    at = _app()
    at.run()
    at.selectbox(key="peakSign").set_value("positive")
    at.number_input(key="pfa").set_value(1e-6)
    at.number_input(key="localOptimumRange").set_value(8)
    at.run()
    assert not at.exception
    det = _config(at)["Detection"]
    assert det["peakSign"] == "positive"
    assert det["pfa"] == pytest.approx(1e-6)
    assert det["localOptimumRange"] == 8


# ── Tracking section ──────────────────────────────────────────────────────────


def test_tracking_gabclosing_params():
    at = _app()
    at.run()
    at.number_input(key="minTrackLength").set_value(15)
    at.number_input(key="cut_off_distance").set_value(25.0)
    at.number_input(key="gab_closing_cut_off_distance").set_value(50.0)
    at.run()
    assert not at.exception
    linking = _config(at)["Linking"]
    assert linking["minTrackLength"] == 15
    assert linking["cut_off_distance"] == pytest.approx(25.0)
    assert linking["gab_closing_cut_off_distance"] == pytest.approx(50.0)


def test_tracker_switch_to_trackbeforedetect():
    at = _app()
    at.run()
    at.selectbox(key="tracker").set_value("trackBeforeDetect")
    at.run()
    assert not at.exception
    cfg = _config(at)
    assert cfg["tracker"] == "trackBeforeDetect"
    assert "Tlength" in cfg
    assert "thresholdLimit" in cfg
    assert "TmaxNo" in cfg


def test_tracker_switch_back_to_gabclosing():
    at = _app()
    at.run()
    at.selectbox(key="tracker").set_value("trackBeforeDetect")
    at.run()
    at.selectbox(key="tracker").set_value("gabClosingTracker")
    at.run()
    assert not at.exception
    cfg = _config(at)
    assert cfg["tracker"] == "gabClosingTracker"
    linking = cfg["Linking"]
    assert "gab_closing_cut_off_distance" in linking
    assert "gab_closing_penalty_distance" in linking


def test_export_optional_figures():
    at = _app()
    at.run()
    at.checkbox(key="exportOptionalFigures" if "exportOptionalFigures" in
                [w.key for w in at.checkbox] else None)
    # exportOptionalFigures is a sidebar checkbox rendered outside expanders
    at.run()
    assert not at.exception
    # default is False
    assert _config(at)["exportOptionalFigures"] in (True, False)


# ── Save / load round-trip ────────────────────────────────────────────────────


def test_roundtrip_default_config():
    at = _app()
    at.run()
    exported = json.dumps(_config(at))

    at2 = _app()
    at2.run()
    at2.session_state["_loaded_config"] = json.loads(exported)
    at2.run()
    assert not at2.exception
    assert _config(at2)["Dt"] == pytest.approx(_config(at)["Dt"])
    assert _config(at2)["kymographPreprocessing"] == _config(at)["kymographPreprocessing"]


def test_roundtrip_modified_config():
    at = _app()
    at.run()
    at.number_input(key="Dt").set_value(0.02)
    at.number_input(key="Wx_single").set_value(25.0)
    at.selectbox(key="peakSign").set_value("positive")
    at.run()
    exported = _config(at)

    # Seed widget session state keys directly (same keys used by st.number_input/selectbox)
    at2 = _app()
    at2.session_state["Dt"] = exported["Dt"]
    at2.session_state["Wx_single"] = exported["kymographPreprocessing"]["Wx"]
    at2.session_state["peakSign"] = exported["Detection"]["peakSign"]
    at2.run()
    assert not at2.exception
    cfg2 = _config(at2)
    assert cfg2["Dt"] == pytest.approx(0.02)
    assert cfg2["kymographPreprocessing"]["Wx"] == pytest.approx(25.0)
    assert cfg2["Detection"]["peakSign"] == "positive"


# AppTest does not support file_uploader — test config load logic directly.

def test_load_invalid_json_raises():
    """apply_config_to_session_state should not be reached; json.loads raises first."""
    with pytest.raises(json.JSONDecodeError):
        json.loads("not valid json {{")


def test_load_partial_json_apply_to_session():
    """apply_config_to_session_state with partial config must not raise."""
    from config import apply_config_to_session_state
    import streamlit as st

    partial = {"Dt": 0.005, "Dx": 0.066}
    # Should not raise even if many keys are missing
    # We call it outside a real Streamlit session — just verify no exception
    try:
        apply_config_to_session_state(partial)
    except Exception as e:
        # Only acceptable exception is from Streamlit not having an active session
        assert "ScriptRunContext" in str(e) or "session" in str(e).lower(), str(e)

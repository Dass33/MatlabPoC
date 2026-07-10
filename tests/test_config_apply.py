"""apply_config must restore every widget-backed field from a config dict.

The mapping is derived from the Config dataclasses (widget keys equal field
names), so a field added to a dataclass + sidebar is restored with no further
bookkeeping. These tests pin the special cases.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest
import streamlit as st
from config import Config, apply_config


@pytest.fixture
def session_state(monkeypatch):
    state: dict = {}
    monkeypatch.setattr(st, "session_state", state)
    return state


def test_restores_fields_from_every_section(session_state):
    cfg = asdict(Config())
    cfg["Dt"] = 0.5
    cfg["kymographPreprocessing"]["Wx"] = 99.0
    cfg["Detection"]["pfa"] = 1e-3
    cfg["Linking"]["minTrackLength"] = 42

    apply_config(cfg)

    assert session_state["Dt"] == 0.5
    assert session_state["Wx"] == 99.0
    assert session_state["pfa"] == 1e-3
    assert session_state["minTrackLength"] == 42


def test_scalar_dark_calibration(session_state):
    apply_config(asdict(Config()))

    assert session_state["dark_cal_mode"] == "Scalar"
    assert session_state["darkCalibration"] == 8.0


def test_template_dark_calibration_keeps_widget_untouched(session_state):
    cfg = asdict(Config())
    cfg["kymographPreprocessing"]["darkCalibration"] = "/opt/templates/foo.mat"

    apply_config(cfg)

    assert session_state["dark_cal_mode"] == "Template"
    assert "darkCalibration" not in session_state


def test_widgetless_fields_are_not_applied(session_state):
    apply_config(asdict(Config()))

    assert "inputDataFormat" not in session_state
    assert "trajectoryProperties" not in session_state


def test_partial_config_applies_only_present_keys(session_state):
    apply_config({"Dt": 0.25})

    assert session_state["Dt"] == 0.25
    assert "Wx" not in session_state
    assert "pfa" not in session_state

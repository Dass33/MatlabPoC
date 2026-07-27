"""apply_settings must seed sidebar widgets from an existing settings document.

This is what the Clone & Re-run flow and the settings uploader rely on: widget
keys are derived from the active preset, so anything the preset exposes picks up
the value the earlier job ran with.
"""

from __future__ import annotations

import config as C
import presets as P
import pytest
import streamlit as st

SETTINGS = {
    "Acquisition": {"Dx": 0.066, "fileExtension": ".tiff"},
    "Detection": {"pfa": 0.00001},
    "Preprocessing": {"darkCalibration": 8.0},
}


@pytest.fixture
def session_state(monkeypatch):
    state: dict = {}
    monkeypatch.setattr(st, "session_state", state)
    return state


@pytest.fixture
def preset():
    p = P.new_preset("Basic", SETTINGS)
    p.updated_at = "2026-07-27T22:00:00+02:00"
    return p


def _item(preset: P.Preset, key: str) -> P.PresetItem:
    item = preset.item(key)
    assert item is not None
    return item


def test_restores_values_the_preset_exposes(session_state, preset):
    C.apply_settings(preset, {"Acquisition": {"Dx": 0.5}, "Detection": {"pfa": 0.1}})

    assert session_state[C.widget_key(preset, _item(preset, "Acquisition.Dx"))] == 0.5
    assert session_state[C.widget_key(preset, _item(preset, "Detection.pfa"))] == 0.1


def test_absent_keys_are_left_alone(session_state, preset):
    C.apply_settings(preset, {"Acquisition": {"Dx": 0.5}})

    assert C.widget_key(preset, _item(preset, "Detection.pfa")) not in session_state


def test_hidden_items_are_not_seeded(session_state, preset):
    item = _item(preset, "Detection.pfa")
    item.ui.visible = False

    C.apply_settings(preset, {"Detection": {"pfa": 0.1}})

    assert C.widget_key(preset, item) not in session_state


def test_file_values_are_reduced_to_a_filename(session_state, preset):
    item = _item(preset, "Preprocessing.darkCalibration")
    item.schema.type = P.FILE

    C.apply_settings(
        preset, {"Preprocessing": {"darkCalibration": "/opt/calibration/c.mat"}}
    )

    assert session_state[C.widget_key(preset, item)] == "c.mat"


def test_widget_keys_are_namespaced_per_preset_and_publish(preset):
    item = _item(preset, "Acquisition.Dx")
    other = P.new_preset("Other", SETTINGS)
    other.updated_at = preset.updated_at
    republished = P.Preset(
        id=preset.id,
        name=preset.name,
        updated_at="2026-07-28T09:00:00+02:00",
        base=preset.base,
        groups=preset.groups,
        items=preset.items,
    )

    assert C.widget_key(preset, item) != C.widget_key(
        other, _item(other, "Acquisition.Dx")
    )
    assert C.widget_key(preset, item) != C.widget_key(republished, item)

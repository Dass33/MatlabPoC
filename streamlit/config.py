"""Preset-driven parameter sidebar.

Which widgets exist, how they are labelled and grouped, and what they start at
all come from the active preset (see presets.py); nothing here is per-parameter
knowledge. The return value is the settings document the job runs with.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import streamlit as st

from presets import (
    BOOL,
    ENUM,
    FILE,
    INTEGER,
    NUMBER,
    Preset,
    PresetItem,
    build_config,
    calibration_files,
    ensure_presets,
    get_path,
)

log = logging.getLogger(__name__)


def widget_key(preset: Preset, item: PresetItem, ns: str | None = None) -> str:
    """Namespaced per preset and per publish.

    The id keeps two presets that expose the same parameter apart; updated_at
    retires the keys of a republished preset, so an open session picks up an
    edited default instead of silently keeping the old one. `ns` overrides the
    publish stamp for the editor's preview, whose widgets must be rebuilt after
    every draft edit (an item can change type under the same key).
    """
    return f"p:{preset.id}:{ns or preset.updated_at}:{item.key}"


def active_preset() -> Preset | None:
    presets = ensure_presets()
    if not presets:
        return None
    selected = st.session_state.get("preset_select")
    return next((p for p in presets if p.id == selected), presets[0])


def apply_settings(preset: Preset, settings: dict) -> None:
    """Seed the sidebar widgets from an existing settings document.

    Used when cloning a job or loading a settings file: any parameter the preset
    exposes takes its value from `settings`, the rest of that document is ignored
    (the preset's own base decides those).
    """
    for item in preset.items:
        value = get_path(settings, item.key)
        if value is None or not item.ui.visible:
            continue
        if item.schema.type == FILE:
            value = str(value).rsplit("/", 1)[-1]
        st.session_state[widget_key(preset, item)] = value


def _number_format(value: float) -> str | None:
    """Small magnitudes need scientific notation or the widget renders them as 0.00."""
    return "%.1e" if value and abs(value) < 1e-3 else None


def _render_item(preset: Preset, item: PresetItem, ns: str | None = None) -> Any:
    schema = item.schema
    key = widget_key(preset, item, ns)
    label = f"{item.label} ({schema.unit})" if schema.unit else item.label
    help_ = item.ui.help or item.key

    if schema.type == BOOL:
        return st.checkbox(label, value=bool(schema.default), key=key, help=help_)

    if schema.type == ENUM:
        options = list(schema.options or [])
        if schema.default in options:
            index = options.index(schema.default)
        else:
            index = 0
            options = (
                [schema.default, *options] if schema.default is not None else options
            )
        if not options:
            st.warning(f"{item.label}: enum with no options")
            return schema.default
        return st.selectbox(label, options, index=index, key=key, help=help_)

    if schema.type == FILE:
        files = calibration_files()
        if not files:
            st.warning(f"{item.label}: no calibration files available")
            return schema.default
        default = str(schema.default).rsplit("/", 1)[-1]
        index = files.index(default) if default in files else 0
        return st.selectbox(label, files, index=index, key=key, help=help_)

    if schema.type == INTEGER:
        return st.number_input(
            label,
            value=int(schema.default or 0),
            min_value=int(schema.min) if schema.min is not None else None,
            max_value=int(schema.max) if schema.max is not None else None,
            # a fractional step stored against an integer item would floor to 0,
            # which number_input rejects
            step=max(1, int(schema.step or 1)),
            key=key,
            help=help_,
        )

    if schema.type == NUMBER:
        value = float(schema.default or 0.0)
        return st.number_input(
            label,
            value=value,
            min_value=float(schema.min) if schema.min is not None else None,
            max_value=float(schema.max) if schema.max is not None else None,
            step=float(schema.step) if schema.step is not None else None,
            format=_number_format(value),
            key=key,
            help=help_,
        )

    return st.text_input(label, value=str(schema.default or ""), key=key, help=help_)


def render_preset_widgets(preset: Preset, ns: str | None = None) -> dict[str, Any]:
    """Render one expander per group into the sidebar; return the values entered.

    Shared by the real sidebar and the editor's preview, which is why it takes a
    key namespace and does no preset selection of its own.
    """
    values: dict[str, Any] = {}
    for group in preset.ordered_groups():
        visible = [i for i in preset.items_in(group) if i.ui.visible]
        if not visible:
            continue
        with st.sidebar.expander(group):
            for item in visible:
                values[item.key] = _render_item(preset, item, ns)
    return values


def render_config_sidebar() -> dict:
    """Sidebar UI for the active preset. Returns a MATLAB-ready settings dict."""
    presets = ensure_presets()

    st.sidebar.header("Algorithm Parameters")

    if not presets:
        st.sidebar.error(
            "No presets available. Open the preset editor (`?preset-editor=on`) to create one."
        )
        return {}

    ids = [p.id for p in presets]
    labels = {p.id: p.name for p in presets}
    selected_id = st.sidebar.selectbox(
        "Preset",
        ids,
        format_func=lambda i: labels[i],
        key="preset_select",
        help="Presets decide which parameters are shown. Edit them in the preset editor.",
    )
    preset = next(p for p in presets if p.id == selected_id)
    if preset.description:
        st.sidebar.caption(preset.description)

    _render_settings_loader(preset)

    config = build_config(preset, render_preset_widgets(preset))

    st.sidebar.download_button(
        "Export current settings",
        data=json.dumps(config, indent=2),
        file_name="settings.json",
        mime="application/json",
        width="stretch",
    )

    return config


def _render_settings_loader(preset: Preset) -> None:
    """Must run before the parameter widgets: session_state cannot be written
    once the widget owning the key exists."""
    with st.sidebar.expander("Load settings"):
        uploaded = st.file_uploader(
            "Settings JSON", type=["json"], key="settings_upload"
        )
        if uploaded is None:
            return

        stamp = (uploaded.name, uploaded.size)
        if st.session_state.get("_settings_upload_stamp") == stamp:
            return
        try:
            apply_settings(preset, json.load(uploaded))
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON in settings file: {e}")
        except (KeyError, TypeError, ValueError) as e:
            st.error(f"Settings format error: {e}")
        else:
            st.session_state["_settings_upload_stamp"] = stamp
            st.rerun()

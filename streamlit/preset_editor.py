"""Preset editor -- the admin page behind `?preset-editor=on`.

Curates which pipeline settings the sidebar exposes: drag items to reorder them
or move them between groups, edit one to change its label, type or default, then
publish. See docs/streamlit/presets.md for what ends up on disk.
"""

from __future__ import annotations

import json

from config import render_preset_widgets
from connectors.storage import list_completed_jobs
from env import job_dirs
from presets import (
    BOOL,
    ENUM,
    FILE,
    INTEGER,
    NUMBER,
    TEXT,
    TYPES,
    ItemSchema,
    ItemUI,
    Preset,
    PresetItem,
    base_settings_files,
    calibration_files,
    delete_preset,
    ensure_presets,
    list_presets,
    new_preset,
    save_preset,
    slugify,
)
from streamlit_dnd import apply_move, dnd

import streamlit as st

DRAFT = "_preset_draft"


def _draft() -> Preset | None:
    return st.session_state.get(DRAFT)


def _load_draft(preset: Preset) -> None:
    st.session_state[DRAFT] = preset
    st.session_state["_draft_id"] = preset.id
    st.session_state["_draft_dirty"] = False
    st.session_state["_draft_rev"] = st.session_state.get("_draft_rev", 0) + 1


def _touch() -> None:
    st.session_state["_draft_dirty"] = True
    st.session_state["_draft_rev"] = st.session_state.get("_draft_rev", 0) + 1


def _container_key(group: str) -> str:
    return f"grp_{slugify(group)}"


@st.dialog("Edit parameter")
def edit_item(item: PresetItem, groups: list[str]) -> None:
    st.caption(item.key)
    schema, ui = item.schema, item.ui

    label = st.text_input("Label", value=item.label)
    group = st.selectbox(
        "Group",
        groups,
        index=groups.index(ui.group) if ui.group in groups else 0,
        accept_new_options=True,
    )
    visible = st.checkbox(
        "Visible",
        value=ui.visible,
        help="Hidden parameters are not shown to users; their default is still sent to MATLAB.",
    )
    type_ = st.selectbox("Type", TYPES, index=TYPES.index(schema.type))

    options = schema.options
    default = schema.default

    if type_ == BOOL:
        default = st.checkbox("Default", value=bool(schema.default))
    elif type_ == ENUM:
        raw = st.text_area(
            "Options (one per line)", value="\n".join(str(o) for o in options or [])
        )
        options = [line.strip() for line in raw.splitlines() if line.strip()]
        default = st.selectbox(
            "Default",
            options or [""],
            index=options.index(str(schema.default))
            if str(schema.default) in options
            else 0,
        )
    elif type_ == FILE:
        files = calibration_files()
        if files:
            current = str(schema.default).rsplit("/", 1)[-1]
            default = st.selectbox(
                "Default calibration file",
                files,
                index=files.index(current) if current in files else 0,
            )
        else:
            st.warning("No calibration files bundled in streamlit/calibration/.")
    elif type_ == TEXT:
        default = st.text_input("Default", value=str(schema.default or ""))
    else:
        cast = int if type_ == INTEGER else float
        try:
            current = cast(schema.default or 0)
        except (TypeError, ValueError):
            current = cast(0)
        default = st.number_input(
            "Default", value=current, format="%g" if cast is float else "%d"
        )

    unit = st.text_input("Unit", value=schema.unit, help="Shown next to the label.")
    help_ = st.text_input("Tooltip", value=ui.help)

    bounds = st.columns(3)
    min_, max_, step = schema.min, schema.max, schema.step
    if type_ in (NUMBER, INTEGER):
        with bounds[0]:
            min_ = _optional_number("Min", schema.min)
        with bounds[1]:
            max_ = _optional_number("Max", schema.max)
        with bounds[2]:
            step = _optional_number("Step", schema.step)

    if st.button("Save", type="primary"):
        item.schema = ItemSchema(
            type=type_,
            default=default,
            options=options if type_ == ENUM else None,
            min=min_,
            max=max_,
            step=step,
            unit=unit.strip(),
        )
        item.ui = ItemUI(
            label=label.strip(), group=group, visible=visible, help=help_.strip()
        )
        draft = _draft()
        if draft and group not in draft.groups:
            draft.groups.append(group)
        _touch()
        st.rerun()


def _optional_number(label: str, value: float | None) -> float | None:
    """A blank text box, because number_input has no empty state."""
    raw = st.text_input(label, value="" if value is None else str(value))
    try:
        return float(raw) if raw.strip() else None
    except ValueError:
        st.error(f"{label} must be a number")
        return value


def _completed_job_configs() -> dict[str, dict]:
    configs = {}
    for job in list_completed_jobs():
        base, _, _ = job_dirs(job["job_id"])
        config_file = base / "config.json"
        if not config_file.is_file():
            continue
        try:
            configs[job.get("name") or job["job_id"]] = json.loads(
                config_file.read_text()
            )
        except (json.JSONDecodeError, OSError):
            continue
    return configs


@st.dialog("New preset")
def new_preset_dialog() -> None:
    name = st.text_input("Name", value="New preset")

    sources = {
        "Bundled base settings": "bundled",
        "Existing preset": "preset",
        "Completed job": "job",
    }
    source = st.radio("Start from", list(sources), horizontal=True)

    base: dict | None = None
    if sources[source] == "bundled":
        bases = base_settings_files()
        if not bases:
            st.error("No bundled base settings found in streamlit/base_settings/.")
        else:
            picked = st.selectbox("Settings file", list(bases))
            base = json.loads(bases[picked].read_text())
    elif sources[source] == "preset":
        existing = {p.name: p for p in list_presets()}
        if not existing:
            st.error("No existing presets to copy.")
        else:
            picked = st.selectbox("Preset", list(existing))
            base = existing[picked].base
    else:
        # The settings a finished job actually ran with -- the way to build a
        # preset for whichever pipeline build is deployed, rather than for the
        # bundled (v2) settings file.
        jobs = _completed_job_configs()
        if not jobs:
            st.error("No completed job has a config to copy.")
        else:
            picked = st.selectbox("Job", list(jobs))
            base = jobs[picked]

    st.caption(
        "A preset is built on a pipeline settings file: every parameter in it is passed "
        "to MATLAB, and the ones you keep visible become sidebar widgets."
    )

    if st.button("Create", type="primary", disabled=base is None):
        assert base is not None
        preset = new_preset(name, base)
        if any(p.id == preset.id for p in list_presets()):
            st.error(f"A preset with id '{preset.id}' already exists.")
            return
        # Saved straight away so it exists in the picker; otherwise the toolbar's
        # selection still names the old preset and reloads over the new draft.
        save_preset(preset)
        st.session_state["_edit_preset_select"] = preset.id
        _load_draft(preset)
        st.rerun()


def _render_item_row(item: PresetItem, groups: list[str]) -> None:
    """One parameter, one line: what users see, what it is, and the two controls
    that matter here -- show/hide and edit."""
    with st.container(key=f"item_{slugify(item.key)}"):
        name, meta, toggle, edit = st.columns(
            [0.6, 0.22, 0.09, 0.09], vertical_alignment="center"
        )
        with name:
            # The dotted path and the default value belong to the edit dialog,
            # where there is room for them.
            if item.ui.visible:
                st.markdown(f"**{item.label}**")
            else:
                st.markdown(f":gray[{item.label}]")
        with meta:
            st.caption(item.schema.type, text_alignment="right")
        with toggle:
            if st.button(
                "",
                icon=":material/visibility:"
                if item.ui.visible
                else ":material/visibility_off:",
                key=f"vis_{item.key}",
                type="tertiary",
                help="Hide from the sidebar"
                if item.ui.visible
                else "Show in the sidebar",
            ):
                item.ui.visible = not item.ui.visible
                _touch()
                st.rerun()
        with edit:
            if st.button(
                "",
                icon=":material/edit:",
                key=f"btn_{item.key}",
                type="tertiary",
                help="Edit label, group, type and default",
            ):
                edit_item(item, groups)


def page_preset_editor() -> None:
    st.header("Preset editor")
    st.caption(
        "Presets decide which pipeline settings users see in the sidebar. "
        "Drag a parameter by its edge to reorder it or move it to another group; "
        "the sidebar on the left previews the result."
    )

    presets = ensure_presets()
    if not presets and _draft() is None:
        st.info("No presets yet.")
        if st.button("New preset", type="primary"):
            new_preset_dialog()
        return

    _render_toolbar(presets)

    draft = _draft()
    if draft is None:
        return

    with st.expander("Preset details"):
        draft.name = st.text_input("Name", value=draft.name, on_change=_touch)
        draft.description = st.text_area(
            "Description",
            value=draft.description,
            height=68,
            on_change=_touch,
            help="Shown under the preset picker in the sidebar.",
        )

    groups = draft.ordered_groups()
    lists = {}
    for position, group in enumerate(groups):
        items = draft.items_in(group)
        _render_group_header(group, position, len(groups))
        with st.container(key=_container_key(group), border=True):
            for item in items:
                _render_item_row(item, groups)
        lists[_container_key(group)] = items

    if st.button("Add group", icon=":material/add:"):
        draft.groups = [*groups, _unused_group_name(groups)]
        _touch()
        st.rerun()

    # "border": the row edges are the drag handle, so the interior stays free for
    # the show/hide and edit buttons and no grip glyph sits on top of the card.
    event = dnd(
        list(lists),
        indicator="ghost",
        handle="border",
        placeholder="Drop parameters here",
    )
    if event:
        apply_move(event, lists)
        _reorder(draft, lists)
        _touch()
        st.rerun()

    _render_publish(draft)
    _render_preview(draft)


def _group_name_key(group: str) -> str:
    """Revision-scoped: a name box keyed only by the old name would come back
    holding the renamed value if a group ever regained its former name."""
    return f"grpname_{st.session_state.get('_draft_rev', 0)}_{slugify(group)}"


def _render_group_header(group: str, position: int, total: int) -> None:
    """A heading with its controls tucked away."""
    name, actions = st.columns([0.91, 0.09], vertical_alignment="center")
    with name:
        st.markdown(f"##### {group}")
    with actions:
        if st.button(
            "",
            icon=":material/more_vert:",
            key=f"grp_menu_{slugify(group)}",
            type="tertiary",
            help="Group settings",
        ):
            edit_group(group, position, total)


@st.dialog("Group settings")
def edit_group(group: str, position: int, total: int) -> None:
    st.text_input(
        "Group name",
        value=group,
        key=_group_name_key(group),
        on_change=_rename_group,
        args=(group,),
        help="Renaming onto another group's name merges the two.",
    )
    up, down = st.columns(2)
    with up:
        if st.button(
            "Move up",
            icon=":material/arrow_upward:",
            key=f"up_{slugify(group)}",
            disabled=position == 0,
            width="stretch",
        ):
            _move_group(group, -1)
            st.rerun()
    with down:
        if st.button(
            "Move down",
            icon=":material/arrow_downward:",
            key=f"down_{slugify(group)}",
            disabled=position == total - 1,
            width="stretch",
        ):
            _move_group(group, 1)
            st.rerun()


def _rename_group(group: str) -> None:
    draft = _draft()
    new = str(st.session_state.get(_group_name_key(group), "")).strip()
    if draft is None or not new or new == group:
        return
    for item in draft.items:
        if item.ui.group == group:
            item.ui.group = new
    # Renaming onto an existing group merges the two, so de-duplicate the order.
    renamed = [new if g == group else g for g in draft.ordered_groups()]
    draft.groups = list(dict.fromkeys(renamed))
    _touch()


def _move_group(group: str, delta: int) -> None:
    draft = _draft()
    if draft is None:
        return
    groups = draft.ordered_groups()
    old = groups.index(group)
    new = max(0, min(len(groups) - 1, old + delta))
    groups.insert(new, groups.pop(old))
    draft.groups = groups
    _touch()


def _unused_group_name(groups: list[str]) -> str:
    n = len(groups) + 1
    while f"Group {n}" in groups:
        n += 1
    return f"Group {n}"


def _render_preview(draft: Preset) -> None:
    """The draft rendered as users would see it, in the real sidebar.

    Keyed on a revision counter that every edit bumps, so a parameter that
    changed type does not hit a widget holding the previous type's value.
    """
    st.sidebar.header("Preview")
    st.sidebar.caption(
        f"{draft.name} - unpublished draft"
        if st.session_state.get("_draft_dirty")
        else draft.name
    )
    render_preset_widgets(draft, ns=f"preview{st.session_state.get('_draft_rev', 0)}")


def _render_toolbar(presets: list[Preset]) -> None:
    select, new, delete = st.columns([0.6, 0.2, 0.2], vertical_alignment="bottom")

    ids = [p.id for p in presets]
    labels = {p.id: p.name for p in presets}
    with select:
        chosen = st.selectbox(
            "Preset to edit",
            ids,
            format_func=lambda i: labels.get(i, str(i)),
            key="_edit_preset_select",
        )
    with new:
        if st.button("New preset", width="stretch"):
            new_preset_dialog()
    with delete:
        if st.button("Delete", type="primary", width="stretch", disabled=not chosen):
            delete_preset(chosen)
            for key in (DRAFT, "_draft_id", "_edit_preset_select"):
                st.session_state.pop(key, None)
            st.rerun()

    if chosen and st.session_state.get("_draft_id") != chosen:
        if st.session_state.get("_draft_dirty"):
            st.warning("Unsaved changes to the previous preset were discarded.")
        loaded = next((p for p in presets if p.id == chosen), None)
        if loaded:
            _load_draft(loaded)


def _reorder(preset: Preset, lists: dict[str, list[PresetItem]]) -> None:
    """Rebuild the flat item list from the per-group containers after a drop.

    Group membership follows the container an item landed in, so dragging across
    groups is how an item is regrouped.
    """
    by_container = {_container_key(g): g for g in preset.ordered_groups()}
    ordered: list[PresetItem] = []
    for container_key, items in lists.items():
        group = by_container.get(container_key, container_key)
        for item in items:
            item.ui.group = group
            ordered.append(item)
    preset.items = ordered


def _render_publish(draft: Preset) -> None:
    st.divider()
    publish, status = st.columns([0.2, 0.8], vertical_alignment="center")
    with publish:
        if st.button("Publish", type="primary", width="stretch"):
            save_preset(draft)
            st.session_state["_draft_dirty"] = False
            st.toast(f"Published '{draft.name}'.")
            st.rerun()
    with status:
        if st.session_state.get("_draft_dirty"):
            st.caption(":orange[Unpublished changes]")
        elif draft.updated_at:
            st.caption(f"Published {draft.updated_at}")


def _leaf_count(node: dict) -> int:
    return sum(_leaf_count(v) if isinstance(v, dict) else 1 for v in node.values())

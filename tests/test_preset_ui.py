"""Preset-driven sidebar and editor page, driven through the real app.

The sidebar has no hardcoded parameters any more, so these pin the two things
that would silently break the app: a preset actually producing widgets, and the
submitted config carrying the parameters the preset does not expose.
"""

from __future__ import annotations

import json

from streamlit.testing.v1 import AppTest

import presets as P

APP = "streamlit/main.py"

SETTINGS = {
    "Acquisition": {"Dx": 0.066, "fileExtension": ".tiff"},
    "Detection": {"peakSign": "negative", "pfa": 0.00001},
    "Export": {"exportImages": True, "trajectoryProperties": ["iOC", "D"]},
}


def _seed_preset(hidden: tuple[str, ...] = (), name: str = "Basic") -> P.Preset:
    preset = P.new_preset(name, SETTINGS)
    for key in hidden:
        item = preset.item(key)
        assert item is not None
        item.ui.visible = False
    P.save_preset(preset)
    return preset


def test_sidebar_renders_widgets_from_the_preset():
    _seed_preset()
    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    labels = [w.label for w in at.sidebar.number_input]
    assert "Dx" in labels
    assert any(cb.label == "Export images" for cb in at.sidebar.checkbox)


def test_hidden_parameters_get_no_widget():
    _seed_preset(hidden=("Acquisition.Dx",))
    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert "Dx" not in [w.label for w in at.sidebar.number_input]


def test_sidebar_seeds_a_preset_when_none_exist():
    """An empty _presets dir must not leave the app with an unusable sidebar."""
    at = AppTest.from_file(APP, default_timeout=30).run()

    assert not at.exception
    assert P.list_presets()
    assert at.sidebar.number_input


def test_editor_page_replaces_the_app_and_lists_parameters():
    _seed_preset()
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["preset-editor"] = "on"
    at.run()

    assert not at.exception
    assert any(h.value == "Preset editor" for h in at.header)
    assert not at.tabs
    # each row is the label and its type; path and default live in the dialog
    assert any(md.value == "**Pfa**" for md in at.markdown)
    assert any(c.value == "number" for c in at.caption)


def test_editor_publishes_the_draft():
    _seed_preset()
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["preset-editor"] = "on"
    at.run()

    publish = [b for b in at.button if b.label == "Publish"]
    assert len(publish) == 1
    publish[0].click().run()

    assert not at.exception
    assert P.list_presets()[0].updated_at


def test_hiding_a_parameter_and_publishing_removes_it_from_the_sidebar():
    """The whole loop: edit the draft, publish, and the sidebar reflects it."""
    _seed_preset()
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["preset-editor"] = "on"
    at.run()

    draft = at.session_state["_preset_draft"]
    item = draft.item("Acquisition.Dx")
    assert item is not None
    item.ui.visible = False
    [b for b in at.button if b.label == "Publish"][0].click().run()
    assert not at.exception

    after = AppTest.from_file(APP, default_timeout=30).run()

    assert not after.exception
    assert "Dx" not in [w.label for w in after.sidebar.number_input]


def _open_editor():
    at = AppTest.from_file(APP, default_timeout=30)
    at.query_params["preset-editor"] = "on"
    return at.run()


def test_group_can_be_renamed_and_takes_its_parameters_with_it():
    _seed_preset()
    at = _open_editor()

    [b for b in at.button if b.key == "grp_menu_Detection"][0].click().run()
    box = [t for t in at.text_input if t.value == "Detection"]
    assert len(box) == 1
    box[0].set_value("Tracking").run()

    assert not at.exception
    draft = at.session_state["_preset_draft"]
    assert [i.key for i in draft.items_in("Tracking")] == [
        "Detection.peakSign",
        "Detection.pfa",
    ]
    assert "Detection" not in draft.ordered_groups()


def test_added_group_is_an_empty_drop_target():
    _seed_preset()
    at = _open_editor()

    [b for b in at.button if b.label == "Add group"][0].click().run()

    assert not at.exception
    draft = at.session_state["_preset_draft"]
    added = draft.ordered_groups()[-1]
    assert draft.items_in(added) == []


def test_editor_previews_the_draft_in_the_sidebar():
    _seed_preset()
    at = _open_editor()

    assert not at.exception
    assert any(h.value == "Preview" for h in at.sidebar.header)
    assert "Dx" in [w.label for w in at.sidebar.number_input]


def test_a_completed_job_can_seed_a_preset(make_upload):
    """How a preset gets authored against whichever pipeline build is deployed."""
    from connectors import storage
    from preset_editor import _completed_job_configs

    old_shape = {"kymographPreprocessing": {"Wx": 15.0}, "Dt": 0.007}
    job_id = storage.create_job([make_upload("a.tif", b"x")], old_shape, name="run one")
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))

    configs = _completed_job_configs()

    assert configs["run one"] == old_shape
    preset = P.new_preset("From job", configs["run one"])
    assert {i.key for i in preset.items} == {"Dt", "kymographPreprocessing.Wx"}


def test_dragging_an_item_into_another_group_regroups_it():
    """Group membership follows the container an item is dropped into."""
    from preset_editor import _container_key, _reorder

    preset = P.new_preset("Basic", SETTINGS)
    moved = preset.item("Detection.pfa")
    assert moved is not None
    lists = {
        _container_key(g): [i for i in preset.items_in(g) if i is not moved]
        for g in preset.ordered_groups()
    }
    lists[_container_key("Acquisition")].insert(0, moved)

    _reorder(preset, lists)

    assert moved.ui.group == "Acquisition"
    assert preset.items[0] is moved
    assert [i.key for i in preset.items_in("Detection")] == ["Detection.peakSign"]
    assert len(preset.items) == len(P.new_preset("Basic", SETTINGS).items)


def test_submitted_config_keeps_parameters_the_preset_hides(make_upload):
    """The pass-through rule: a hidden parameter is still sent to MATLAB."""
    _seed_preset(hidden=("Acquisition.Dx",))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception

    from connectors import storage

    job_id = storage.create_job([make_upload("a.tif", b"x")], _submitted_config(at))
    base, _, _ = storage.job_dirs(job_id)
    config = json.loads((base / "config.json").read_text())

    assert config["Acquisition"]["Dx"] == 0.066
    assert config["Export"]["trajectoryProperties"] == ["iOC", "D"]


def _submitted_config(at) -> dict:
    """Rebuild what main.py passes to the Submit tab from the rendered sidebar."""
    preset = P.list_presets()[0]
    values = {
        i.key: w.value
        for i in preset.items
        if i.ui.visible
        for w in [*at.sidebar.number_input, *at.sidebar.checkbox, *at.sidebar.selectbox]
        if w.label in (i.label, f"{i.label} ({i.schema.unit})")
    }
    return P.build_config(preset, values)

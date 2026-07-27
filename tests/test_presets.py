"""Preset format: path handling, derivation from a settings file, config emission.

The load/save helpers write into the per-test data dir (conftest patches
env.DATA_DIR), but presets.PRESETS_DIR binds DATA_DIR at import, so tests that
touch disk repoint it explicitly.
"""

from __future__ import annotations

import json

import presets as P
import pytest


@pytest.fixture(autouse=True)
def presets_dir(tmp_path, monkeypatch):
    d = tmp_path / "_presets"
    monkeypatch.setattr(P, "PRESETS_DIR", d)
    return d


SETTINGS = {
    "Acquisition": {
        "fileExtension": ".tiff",
        "Dx": 0.066,
        "Channel": {"width_nm": 200.0, "area_um2": 0.04},
    },
    "Detection": {"peakSign": "negative", "pfa": 0.00001, "localOptimumRange": 6.0},
    "Export": {"exportImages": True, "trajectoryProperties": ["iOC", "D"]},
}


def test_get_and_set_nested_path():
    settings = {"a": {"b": {"c": 1}}}

    assert P.get_path(settings, "a.b.c") == 1
    assert P.get_path(settings, "a.b.missing") is None
    assert P.get_path(settings, "a.b.c.deeper") is None

    P.set_path(settings, "a.b.c", 2)
    P.set_path(settings, "a.new.leaf", "x")

    assert settings["a"]["b"]["c"] == 2
    assert settings["a"]["new"]["leaf"] == "x"


def test_derive_items_covers_scalars_and_skips_lists():
    items = {i.key: i for i in P.derive_items(SETTINGS)}

    assert "Acquisition.Channel.width_nm" in items
    assert items["Detection.pfa"].schema.type == P.NUMBER
    assert items["Detection.peakSign"].schema.type == P.TEXT
    assert items["Export.exportImages"].schema.type == P.BOOL
    # lists are not editable scalars, so they only ever pass through in `base`
    assert "Export.trajectoryProperties" not in items


def test_top_level_scalars_share_one_group():
    """A flat settings file must not give every parameter an expander of its own."""
    items = P.derive_items(
        {"Dt": 0.007, "Dx": 0.066, "Linking": {"minTrackLength": 10}}
    )

    groups = {i.key: i.ui.group for i in items}
    assert groups == {
        "Dt": P.DEFAULT_GROUP,
        "Dx": P.DEFAULT_GROUP,
        "Linking.minTrackLength": "Linking",
    }


def test_declared_groups_survive_while_empty():
    """The editor needs empty groups to exist as drop targets."""
    preset = P.new_preset("Basic", SETTINGS)
    preset.groups = [*preset.groups, "Tracking"]

    assert "Tracking" in preset.ordered_groups()


def test_derived_item_groups_and_labels():
    items = {i.key: i for i in P.derive_items(SETTINGS)}

    nested = items["Acquisition.Channel.width_nm"]
    assert nested.ui.group == "Acquisition"
    assert nested.label == "Width nm"
    assert items["Detection.localOptimumRange"].label == "Local optimum range"


def test_build_config_passes_through_uncovered_keys():
    preset = P.new_preset("Basic", SETTINGS)
    preset.items = [i for i in preset.items if i.key == "Detection.pfa"]

    config = P.build_config(preset, {"Detection.pfa": 0.1})

    assert config["Detection"]["pfa"] == 0.1
    assert config["Export"]["trajectoryProperties"] == ["iOC", "D"]
    assert config["Acquisition"]["Channel"]["area_um2"] == 0.04


def test_build_config_writes_default_for_hidden_items():
    preset = P.new_preset("Basic", SETTINGS)
    hidden = preset.item("Acquisition.Dx")
    assert hidden is not None
    hidden.ui.visible = False
    hidden.schema.default = 0.1

    config = P.build_config(preset, {"Acquisition.Dx": 999.0})

    assert config["Acquisition"]["Dx"] == 0.1


def test_build_config_does_not_mutate_base():
    preset = P.new_preset("Basic", SETTINGS)

    P.build_config(preset, {"Acquisition.Dx": 1.0})

    assert preset.base["Acquisition"]["Dx"] == 0.066


def test_file_items_leave_as_absolute_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(P, "CALIBRATION_DIR", tmp_path)
    preset = P.new_preset("Basic", {"Preprocessing": {"darkCalibration": 8.0}})
    item = preset.item("Preprocessing.darkCalibration")
    assert item is not None
    item.schema.type = P.FILE

    config = P.build_config(preset, {"Preprocessing.darkCalibration": "cal.mat"})

    assert config["Preprocessing"]["darkCalibration"] == str(tmp_path / "cal.mat")


def test_save_and_load_round_trip(presets_dir):
    preset = P.new_preset("Basic scan", SETTINGS)
    preset.description = "hello"
    item = preset.item("Detection.peakSign")
    assert item is not None
    item.schema.type = P.ENUM
    item.schema.options = ["negative", "positive"]
    item.ui.group = "Tracking"

    P.save_preset(preset)
    loaded = P.load_preset("Basic_scan")

    assert loaded is not None
    assert loaded.name == "Basic scan"
    assert loaded.description == "hello"
    assert loaded.updated_at
    assert [i.key for i in loaded.items] == [i.key for i in preset.items]
    reloaded_item = loaded.item("Detection.peakSign")
    assert reloaded_item is not None
    assert reloaded_item.schema.options == ["negative", "positive"]
    assert reloaded_item.ui.group == "Tracking"


def test_item_order_is_render_order(presets_dir):
    preset = P.new_preset("Basic", SETTINGS)
    preset.items.reverse()
    expected = [i.key for i in preset.items]

    P.save_preset(preset)

    loaded = P.load_preset("Basic")
    assert loaded is not None
    assert [i.key for i in loaded.items] == expected


def test_ordered_groups_appends_groups_missing_from_the_list():
    preset = P.new_preset("Basic", SETTINGS)
    preset.groups = ["Detection"]

    groups = preset.ordered_groups()

    assert groups[0] == "Detection"
    assert set(groups) == {"Acquisition", "Detection", "Export"}


def test_v1_preset_is_converted_on_read(presets_dir):
    presets_dir.mkdir(parents=True)
    old = {
        "name": "Basic",
        "config": {"Dt": 0.007, "kymographPreprocessing": {"Wx": 15.0}},
    }
    (presets_dir / "Basic.json").write_text(json.dumps(old))

    loaded = P.list_presets()

    assert len(loaded) == 1
    preset = loaded[0]
    assert preset.name == "Basic"
    assert preset.base == old["config"]
    assert {i.key for i in preset.items} == {"Dt", "kymographPreprocessing.Wx"}
    # a v1 file stays untouched on disk until it is published from the editor
    assert json.loads((presets_dir / "Basic.json").read_text()) == old


def test_unreadable_preset_is_skipped_not_fatal(presets_dir):
    presets_dir.mkdir(parents=True)
    (presets_dir / "broken.json").write_text("{not json")
    P.save_preset(P.new_preset("Good", SETTINGS))

    loaded = P.list_presets()

    assert [p.name for p in loaded] == ["Good"]


def test_delete_preset(presets_dir):
    P.save_preset(P.new_preset("Doomed", SETTINGS))

    P.delete_preset("Doomed")

    assert P.list_presets() == []


def test_ensure_presets_seeds_from_bundled_base_settings(presets_dir):
    seeded = P.ensure_presets()

    assert seeded
    assert P.get_path(seeded[0].base, "Detection.pfa") is not None
    assert (presets_dir / f"{seeded[0].id}.json").is_file()


def test_ensure_presets_leaves_existing_presets_alone(presets_dir):
    P.save_preset(P.new_preset("Mine", SETTINGS))

    assert [p.name for p in P.ensure_presets()] == ["Mine"]


def test_bundled_base_settings_are_shipped():
    """The MATLAB submodule is not in the image, so these copies are the catalog."""
    bases = P.base_settings_files()

    assert "Setting_default" in bases
    assert P.get_path(
        json.loads(bases["Setting_default"].read_text()), "Linking.cut_off_distance"
    )

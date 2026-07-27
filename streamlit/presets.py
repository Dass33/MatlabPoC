"""Preset format and storage.

A preset says which pipeline settings the sidebar exposes, how they are grouped
and labelled, and what they default to -- see docs/streamlit/presets.md for the
on-disk format. Everything here is pure data handling; the sidebar lives in
config.py and the authoring UI in preset_editor.py.
"""

from __future__ import annotations

import copy
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from env import CALIBRATION_DIR, DATA_DIR, TZ

log = logging.getLogger(__name__)

PRESETS_DIR = DATA_DIR / "_presets"
BASE_SETTINGS_DIR = Path(__file__).parent / "base_settings"
FORMAT_VERSION = 2

NUMBER, INTEGER, BOOL, ENUM, TEXT, FILE = (
    "number",
    "integer",
    "bool",
    "enum",
    "text",
    "file",
)
TYPES = (NUMBER, INTEGER, BOOL, ENUM, TEXT, FILE)


@dataclass
class ItemSchema:
    """Semantic facts about a parameter. Moves upstream once MATLAB owns a schema."""

    type: str = NUMBER
    default: Any = 0.0
    options: list[Any] | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None
    unit: str = ""

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type, "default": self.default}
        for name in ("options", "min", "max", "step", "unit"):
            value = getattr(self, name)
            if value not in (None, ""):
                d[name] = value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ItemSchema:
        type_ = d.get("type", NUMBER)
        if type_ not in TYPES:
            log.warning("[presets] unknown type %r, treating as text", type_)
            type_ = TEXT
        return cls(
            type=type_,
            default=d.get("default"),
            options=d.get("options"),
            min=d.get("min"),
            max=d.get("max"),
            step=d.get("step"),
            unit=d.get("unit", ""),
        )


@dataclass
class ItemUI:
    """How the parameter is presented. Owned by this app, never by the pipeline."""

    label: str = ""
    group: str = "General"
    visible: bool = True
    help: str = ""

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "label": self.label,
            "group": self.group,
            "visible": self.visible,
        }
        if self.help:
            d["help"] = self.help
        return d

    @classmethod
    def from_dict(cls, d: dict) -> ItemUI:
        return cls(
            label=d.get("label", ""),
            group=d.get("group", "General"),
            visible=bool(d.get("visible", True)),
            help=d.get("help", ""),
        )


@dataclass
class PresetItem:
    key: str
    schema: ItemSchema = field(default_factory=ItemSchema)
    ui: ItemUI = field(default_factory=ItemUI)

    @property
    def label(self) -> str:
        return self.ui.label or humanize(self.key.rsplit(".", 1)[-1])

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "schema": self.schema.to_dict(),
            "ui": self.ui.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> PresetItem:
        return cls(
            key=d["key"],
            schema=ItemSchema.from_dict(d.get("schema", {})),
            ui=ItemUI.from_dict(d.get("ui", {})),
        )


@dataclass
class Preset:
    id: str
    name: str
    description: str = ""
    updated_at: str = ""
    base: dict = field(default_factory=dict)
    groups: list[str] = field(default_factory=list)
    items: list[PresetItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "version": FORMAT_VERSION,
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "updated_at": self.updated_at,
            "base": self.base,
            "groups": self.ordered_groups(),
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Preset:
        if d.get("version") != FORMAT_VERSION:
            return _from_v1(d)
        return cls(
            id=d["id"],
            name=d.get("name", d["id"]),
            description=d.get("description", ""),
            updated_at=d.get("updated_at", ""),
            base=d.get("base", {}),
            groups=list(d.get("groups", [])),
            items=[PresetItem.from_dict(i) for i in d.get("items", [])],
        )

    def ordered_groups(self) -> list[str]:
        """Declared group order, with any group only an item knows about appended.

        Declared groups are kept even when empty: the editor needs somewhere to
        drop items into, and the sidebar skips groups with nothing visible.
        """
        seen = list(self.groups)
        for item in self.items:
            if item.ui.group not in seen:
                seen.append(item.ui.group)
        return seen

    def items_in(self, group: str) -> list[PresetItem]:
        return [i for i in self.items if i.ui.group == group]

    def item(self, key: str) -> PresetItem | None:
        return next((i for i in self.items if i.key == key), None)


def humanize(name: str) -> str:
    """cut_off_distance -> Cut off distance, maxPositiveGap -> Max positive gap."""
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", name.replace("_", " ")).split()
    if not words:
        return name
    # Only plain Titlecase words are lowered, so acronyms (iOC, nm, PSF) survive.
    tail = [w.lower() if w.istitle() else w for w in words[1:]]
    return " ".join([words[0][:1].upper() + words[0][1:], *tail])


def slugify(name: str) -> str:
    return re.sub(r"[^\w.-]+", "_", name.strip()).strip("_") or "preset"


def get_path(settings: dict, key: str) -> Any:
    node: Any = settings
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def set_path(settings: dict, key: str, value: Any) -> None:
    parts = key.split(".")
    node = settings
    for part in parts[:-1]:
        child = node.get(part)
        if not isinstance(child, dict):
            child = {}
            node[part] = child
        node = child
    node[parts[-1]] = value


def infer_schema(value: Any) -> ItemSchema | None:
    """Schema for a settings leaf, or None if it is not an editable scalar."""
    if isinstance(value, bool):
        return ItemSchema(type=BOOL, default=value)
    if isinstance(value, int):
        return ItemSchema(type=INTEGER, default=value, step=1)
    if isinstance(value, float):
        # jsondecode gives every MATLAB number as a double, so whole values
        # like 150.0 are still free-form numbers, not integers.
        return ItemSchema(type=NUMBER, default=value, step=_step_for(value))
    if isinstance(value, str):
        return ItemSchema(type=TEXT, default=value)
    return None


def _step_for(value: float) -> float:
    magnitude = abs(value)
    if magnitude == 0 or magnitude >= 10:
        return 1.0
    if magnitude >= 1:
        return 0.1
    return 0.001


DEFAULT_GROUP = "General"


def derive_items(settings: dict) -> list[PresetItem]:
    """One item per editable scalar leaf, grouped by the section it sits in.

    A leaf at the top level has no section to name it, so it goes to a shared
    group -- otherwise a flat settings file gives every parameter a group of its
    own, which is one expander per parameter in the sidebar.
    """
    items: list[PresetItem] = []

    def walk(node: dict, path: list[str]) -> None:
        for name, value in node.items():
            here = [*path, name]
            if isinstance(value, dict):
                walk(value, here)
                continue
            schema = infer_schema(value)
            if schema is None:
                continue
            key = ".".join(here)
            group = here[0] if len(here) > 1 else DEFAULT_GROUP
            items.append(
                PresetItem(
                    key=key,
                    schema=schema,
                    ui=ItemUI(label=humanize(name), group=group, visible=True),
                )
            )

    walk(settings, [])
    return items


def new_preset(name: str, base: dict) -> Preset:
    items = derive_items(base)
    groups: list[str] = []
    for item in items:
        if item.ui.group not in groups:
            groups.append(item.ui.group)
    return Preset(
        id=slugify(name),
        name=name.strip() or "Untitled",
        base=copy.deepcopy(base),
        groups=groups,
        items=items,
    )


def calibration_files() -> list[str]:
    if not CALIBRATION_DIR.is_dir():
        return []
    return sorted(f.name for f in CALIBRATION_DIR.glob("*.mat"))


def resolve_value(item: PresetItem, value: Any) -> Any:
    """Widget value as MATLAB should see it.

    A `file` item is stored as a bare filename so a preset stays portable, but
    the pipeline `load()`s the path it is given, so it has to leave here absolute.
    """
    if item.schema.type == FILE and isinstance(value, str) and value:
        return str(CALIBRATION_DIR / Path(value).name)
    return value


def build_config(preset: Preset, values: dict[str, Any] | None = None) -> dict:
    """The settings document a job runs with: base, overwritten by preset items.

    Keys of `base` that no item covers pass through untouched, so a parameter the
    preset does not know about is still handed to MATLAB as the pipeline shipped it.
    """
    values = values or {}
    config = copy.deepcopy(preset.base)
    for item in preset.items:
        value = values.get(item.key) if item.ui.visible else None
        if value is None:
            value = item.schema.default
        set_path(config, item.key, resolve_value(item, value))
    return config


def _from_v1(d: dict) -> Preset:
    """Convert a v1 value-snapshot preset ({"name", "config"}) into a v2 preset."""
    name = d.get("name", "Imported")
    config = d.get("config", {})
    preset = new_preset(name, config)
    preset.description = "Converted from the old value-snapshot format."
    return preset


def list_presets() -> list[Preset]:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    presets = []
    for f in sorted(PRESETS_DIR.glob("*.json")):
        try:
            presets.append(Preset.from_dict(json.loads(f.read_text())))
        except (json.JSONDecodeError, OSError, KeyError, TypeError) as e:
            log.warning("[presets] skipping %s: %s", f.name, e)
    return presets


def load_preset(preset_id: str) -> Preset | None:
    return next((p for p in list_presets() if p.id == preset_id), None)


def save_preset(preset: Preset) -> Path:
    PRESETS_DIR.mkdir(parents=True, exist_ok=True)
    preset.updated_at = datetime.now(TZ).isoformat(timespec="seconds")
    path = PRESETS_DIR / f"{preset.id}.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(preset.to_dict(), indent=2))
    tmp.replace(path)
    return path


def delete_preset(preset_id: str) -> None:
    (PRESETS_DIR / f"{preset_id}.json").unlink(missing_ok=True)


def base_settings_files() -> dict[str, Path]:
    if not BASE_SETTINGS_DIR.is_dir():
        return {}
    return {f.stem: f for f in sorted(BASE_SETTINGS_DIR.glob("*.json"))}


def ensure_presets() -> list[Preset]:
    """Presets on disk, seeding one from the bundled base settings if there are none."""
    presets = list_presets()
    if presets:
        return presets

    bases = base_settings_files()
    if not bases:
        log.warning("[presets] no presets and no bundled base settings to seed from")
        return []

    name, path = next(iter(bases.items()))
    try:
        preset = new_preset(humanize(name), json.loads(path.read_text()))
    except (json.JSONDecodeError, OSError) as e:
        log.error("[presets] could not seed from %s: %s", path, e)
        return []
    save_preset(preset)
    log.info("[presets] seeded %r from %s", preset.name, path.name)
    return [preset]

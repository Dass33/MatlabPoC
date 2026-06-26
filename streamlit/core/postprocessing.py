from __future__ import annotations

from typing import TypedDict

import numpy as np

from connectors.matlab_bridge import Collection, MatlabFilterSetting

MICRO_PROPS: frozenset[str] = frozenset({"iOC", "STDiOC"})

AVAILABLE_PROPS: list[str] = [
    "iOC",
    "D",
    "STDiOC",
    "velocity",
    "N",
    "positionStart",
    "positionEnd",
]

FILTER_DEFAULTS: dict[str, dict[str, str]] = {
    "iOC": {"direction": "both", "tv": "3std"},
    "STDiOC": {"direction": "upper", "tv": "3std_conditional"},
    "D": {"direction": "both", "tv": "3std"},
    "velocity": {"direction": "both", "tv": "3std"},
    "N": {"direction": "lower", "tv": "3std"},
    "positionStart": {"direction": "upper", "tv": "3std"},
    "positionEnd": {"direction": "lower", "tv": "3std"},
}

SCALAR_PROPS: list[str] = list(FILTER_DEFAULTS)
TV_OPTIONS: list[str] = ["3std", "3std_conditional", "number"]
DIR_OPTIONS: list[str] = ["upper", "lower", "both"]


class ThresholdConfig(TypedDict):
    enabled: bool
    direction: str
    tv: str
    value: float
    value_lo: float
    value_hi: float


def compute_states(
    n: int, not_outlier: np.ndarray, overrides: dict[int, str]
) -> list[str]:
    return [
        ("manual-kept" if overrides[i] == "kept" else "manual-excluded")
        if i in overrides
        else ("auto-kept" if not_outlier[i] else "auto-excluded")
        for i in range(n)
    ]


def build_matlab_setting(
    thresholds: dict[str, ThresholdConfig],
) -> MatlabFilterSetting:
    active_props = []
    threshold_values = []
    directions = []
    for prop in FILTER_DEFAULTS:
        cfg = thresholds[prop]
        if not cfg.get("enabled", True):
            continue
        tv = cfg.get("tv", "3std")
        direction = cfg.get("direction", "upper")
        active_props.append(prop)
        directions.append(direction)
        if tv == "number":
            scale = 1e-6 if prop in MICRO_PROPS else 1.0
            if direction == "both":
                threshold_values.append([
                    cfg.get("value_lo", 0.0) * scale,
                    cfg.get("value_hi", 0.0) * scale,
                ])
            else:
                threshold_values.append([cfg.get("value", 0.0) * scale])
        else:
            threshold_values.append(tv)
    return {
        "filterProperties": active_props,
        "thresholdDirection": directions,
        "thresholdValue": threshold_values,
        "referenceProperty": "iOC",
    }


def filter_collection(
    collection: Collection, keep_mask: np.ndarray
) -> dict[str, object]:
    result = {}
    for k, v in collection.items():
        if isinstance(v, np.ndarray) and len(v) == len(keep_mask):
            result[k] = v[keep_mask].tolist()
        elif isinstance(v, (list, tuple)) and len(v) == len(keep_mask):
            result[k] = [v[i] for i, m in enumerate(keep_mask) if m]
    return result

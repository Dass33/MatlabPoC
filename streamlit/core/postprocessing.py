from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from connectors.algorithms import Collection, MatlabFilterSetting

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

_REFERENCE_PROP = "iOC"


@dataclass
class ThresholdConfig:
    enabled: bool
    direction: str
    tv: str
    value: float = 0.0
    value_lo: float = 0.0
    value_hi: float = 0.0


def default_thresholds() -> dict[str, ThresholdConfig]:
    return {
        p: ThresholdConfig(enabled=True, direction=d["direction"], tv=d["tv"])
        for p, d in FILTER_DEFAULTS.items()
    }


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
        if not cfg.enabled:
            continue
        active_props.append(prop)
        directions.append(cfg.direction)
        if cfg.tv == "number":
            scale = 1e-6 if prop in MICRO_PROPS else 1.0
            if cfg.direction == "both":
                threshold_values.append([cfg.value_lo * scale, cfg.value_hi * scale])
            else:
                threshold_values.append([cfg.value * scale])
        else:
            threshold_values.append(cfg.tv)
    return {
        "filterProperties": active_props,
        "thresholdDirection": directions,
        "thresholdValue": threshold_values,
        "referenceProperty": _REFERENCE_PROP,
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

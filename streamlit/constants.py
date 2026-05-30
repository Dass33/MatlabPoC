from __future__ import annotations

from typing import Any

DEFAULT_CONFIG: dict[str, Any] = {
    "exportOptionalFigures": False,
    "inputDataFormat": "tiff2",
    "Dt": 0.007,
    "Dx": 0.066,
    "flipIntensity": True,
    "flowEstimate": -3.4,
    "kymographPreprocessing": {
        "darkCalibration": 8,
        "Wx": 15,
        "Wt": 50,
        "ws": 2.36,
        "removeBackground": "movmedian",
    },
    "Detection": {"peakSign": "negative", "pfa": 1e-5, "localOptimumRange": 6},
    "tracker": "gabClosingTracker",
    "Tlength": 4,
    "thresholdLimit": -2.0,
    "TmaxNo": 8,
    "Linking": {
        "minTrackLength": 10,
        "cut_off_distance": 20,
        "unmatched_penalty_distance": 15,
        "maxNegativeGab": 2,
        "maxPositiveGab": 3,
        "gab_closing_cut_off_distance": 40,
        "gab_closing_penalty_distance": 30,
    },
    "trajectoryProperties": [
        "positionRefined",
        "timeFrame",
        "iOCprofile",
        "N",
        "iOC",
        "STDiOC",
        "D",
        "velocity",
    ],
}

STATUS_ICON: dict[str, str] = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}

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
    "STDiOC": {"direction": "upper", "tv": "3std"},
    "D": {"direction": "both", "tv": "3std"},
    "velocity": {"direction": "both", "tv": "3std"},
    "N": {"direction": "lower", "tv": "3std"},
    "positionStart": {"direction": "upper", "tv": "3std"},
    "positionEnd": {"direction": "lower", "tv": "3std"},
}

SCALAR_PROPS: list[str] = list(FILTER_DEFAULTS)

TV_OPTIONS: list[str] = ["3std", "3std_conditional", "number"]
DIR_OPTIONS: list[str] = ["upper", "lower", "both"]

STATES: dict[str, tuple[str, str]] = {
    "auto-kept": ("#0072B2", "circle"),
    "auto-excluded": ("#D55E00", "x"),
    "manual-kept": ("#009E73", "diamond"),
    "manual-excluded": ("#E69F00", "square"),
}

TRACK_PALETTE: list[str] = [
    "#e6194B",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#42d4f4",
    "#f032e6",
    "#bfef45",
    "#469990",
    "#dcbeff",
    "#9A6324",
    "#800000",
    "#aaffc3",
    "#000075",
]

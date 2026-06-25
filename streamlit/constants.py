from __future__ import annotations

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

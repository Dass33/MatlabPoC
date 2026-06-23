from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import numpy as np


# ─── serialisation helpers ───────────────────────────────────────────────────
def to_json(obj: Any) -> str:
    def _default(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        raise TypeError(type(o))

    return json.dumps(obj, default=_default)


def prep_collection(collection: Mapping[str, Any]) -> dict[str, Any]:
    """Convert numpy arrays to plain Python lists for JSON serialisation."""
    out: dict = {}
    for k, v in collection.items():
        if isinstance(v, np.ndarray):
            out[k] = v.tolist()
        elif isinstance(v, (list, tuple)) and v and isinstance(v[0], np.ndarray):
            out[k] = [a.tolist() for a in v]
        else:
            out[k] = v
    return out

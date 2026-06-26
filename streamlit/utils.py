from __future__ import annotations

import json
from typing import Any

import numpy as np


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

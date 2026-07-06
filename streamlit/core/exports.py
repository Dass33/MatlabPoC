from __future__ import annotations

import io
import logging
from typing import Any

import numpy as np
import pandas as pd
import scipy.io

log = logging.getLogger(__name__)

_MICRO_PROPS = frozenset({"iOC", "STDiOC"})
_PREFERRED_ORDER = ["iOC", "STDiOC", "N", "D", "velocity"]


def _is_scalar_prop(values: Any) -> bool:
    return isinstance(values, list) and all(
        isinstance(v, (int, float)) and not isinstance(v, bool) for v in values
    )


def trajectories_csv(collection: dict) -> str:
    scalar_props = [k for k, v in collection.items() if _is_scalar_prop(v)]
    ordered = [p for p in _PREFERRED_ORDER if p in scalar_props] + sorted(
        p for p in scalar_props if p not in _PREFERRED_ORDER
    )

    data: dict[str, list[float]] = {}
    for prop in ordered:
        values = collection[prop]
        if prop in _MICRO_PROPS:
            data[f"{prop} (µ)"] = [v * 1e6 for v in values]
        else:
            data[prop] = values

    df = pd.DataFrame(data)
    df.insert(0, "trajectory", np.arange(len(df)))
    return df.to_csv(index=False)


def _sanitize(value: Any) -> Any:
    # savemat rejects None wherever it appears; JSON round-trips MATLAB NaN as null,
    # so mapping it back to NaN keeps this consistent with collection.mat.
    if value is None:
        return np.nan
    if isinstance(value, dict):
        return {k: _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        if value and isinstance(value[0], list):
            arr = np.empty(len(value), dtype=object)
            for i, v in enumerate(value):
                arr[i] = np.asarray(_sanitize(v))
            return arr
        return [_sanitize(v) for v in value]
    return value


def collection_mat(data: dict) -> bytes:
    payload: dict[str, Any] = {"collection": _sanitize(data.get("collection", {}))}
    for key in ("n_kept", "n_total", "calibration"):
        if data.get(key) is not None:
            payload[key] = _sanitize(data[key])

    buffer = io.BytesIO()
    scipy.io.savemat(buffer, payload, do_compression=True)
    return buffer.getvalue()

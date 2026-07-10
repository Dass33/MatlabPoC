"""Shared synthetic-but-algorithm-valid NSM data for tests.

The key constraint (learned from iOCcalibration.m) is that per-trajectory
positionRefined vectors must overlap, so a shared position grid is used.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import scipy.io


def sample_collection(n: int = 10, length: int = 30) -> dict:
    """Synthetic collection valid for BOTH the outlier filter and iOC calibration.

    Two independent constraints have to hold at once:
    - Calibration (iOCcalibration.m) forms x = max(per-traj mins):min(per-traj maxes)
      over positionRefined, so the trajectories must OVERLAP in position.
    - The default outlier filter runs 3-std thresholds on every scalar property, so
      those (N, positionStart/End, D, velocity, iOC) need real spread or the filter
      marks everything an outlier and calibration then runs on an empty subset.

    So: each trajectory gets a small random start offset and length (giving scalar
    spread) while all still cover a common window [max(start), min(end)] (giving
    overlap). Scalars are derived from the per-frame vectors so they stay consistent.
    """
    rng = np.random.default_rng(0)
    starts = rng.integers(0, 5, n)
    lengths = length + rng.integers(-4, 5, n)
    positions = [np.arange(s, s + ln, dtype=float) for s, ln in zip(starts, lengths)]
    profiles = [np.abs(rng.normal(1e-6, 1.5e-7, ln)) for ln in lengths]
    return {
        "iOC": np.array([p.mean() for p in profiles]),
        "STDiOC": np.array([p.std() for p in profiles]),
        "N": lengths.astype(float),
        "D": np.abs(rng.normal(1.0, 0.15, n)),
        "velocity": rng.normal(0.0, 0.5, n),
        "positionRefined": positions,
        "timeFrame": [np.arange(ln, dtype=float) for ln in lengths],
        "iOCprofile": profiles,
        "positionStart": np.array([p[0] for p in positions]),
        "positionEnd": np.array([p[-1] for p in positions]),
    }


def _to_matlab_struct(collection: dict) -> dict:
    """Encode cell fields (lists of per-trajectory vectors) as object arrays so
    scipy.io.savemat writes them as MATLAB cells and loadmat round-trips them the
    way the postprocessing tab's loader expects."""
    out: dict = {}
    for k, v in collection.items():
        if isinstance(v, list):
            arr = np.empty(len(v), dtype=object)
            for i, x in enumerate(v):
                arr[i] = np.asarray(x, dtype=float)
            out[k] = arr
        else:
            out[k] = np.asarray(v)
    return out


def write_collection_mat(out_dir: Path, collection: dict) -> Path:
    """Write out_dir/collection/collection.mat as the tabs expect it."""
    coll_dir = out_dir / "collection"
    coll_dir.mkdir(parents=True, exist_ok=True)
    path = coll_dir / "collection.mat"
    scipy.io.savemat(str(path), {"collection": _to_matlab_struct(collection)})
    return path

from __future__ import annotations

import io

import numpy as np
import scipy.io

from core.exports import collection_mat, trajectories_csv


def test_trajectories_csv_orders_and_scales_micro_props():
    collection = {
        "velocity": [10.0, 20.0],
        "iOC": [1e-6, 2e-6],
        "N": [3, 4],
        "notes": ["x", "y"],  # non-scalar -> excluded
    }
    csv = trajectories_csv(collection)
    header = csv.splitlines()[0].split(",")
    # trajectory index first, then preferred order (iOC, N) before others (velocity)
    assert header[0] == "trajectory"
    assert header.index("iOC (µ)") < header.index("N") < header.index("velocity")
    assert "notes" not in header
    # micro prop scaled to µ
    first_row = csv.splitlines()[1].split(",")
    assert first_row[header.index("iOC (µ)")] == "1.0"


def test_collection_mat_none_becomes_nan_and_roundtrips():
    data = {"collection": {"iOC": [1.0, None, 3.0]}, "n_kept": 2, "n_total": 3}
    raw = collection_mat(data)
    loaded = scipy.io.loadmat(io.BytesIO(raw), squeeze_me=True)
    ioc = loaded["collection"]["iOC"].item()
    assert ioc[0] == 1.0 and np.isnan(ioc[1]) and ioc[2] == 3.0
    assert int(loaded["n_kept"]) == 2


def test_collection_mat_omits_absent_optional_keys():
    raw = collection_mat({"collection": {"iOC": [1.0]}})
    loaded = scipy.io.loadmat(io.BytesIO(raw))
    assert "calibration" not in loaded
    assert "n_kept" not in loaded

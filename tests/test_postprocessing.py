from __future__ import annotations

import numpy as np
import pytest

from core.postprocessing import (
    ThresholdConfig,
    build_matlab_setting,
    compute_states,
    default_thresholds,
    filter_collection,
    thresholds_from_jsonable,
    thresholds_to_jsonable,
)


def test_build_matlab_setting_skips_disabled():
    thr = default_thresholds()
    thr["D"].enabled = False
    setting = build_matlab_setting(thr)
    assert "D" not in setting["filterProperties"]
    assert "iOC" in setting["filterProperties"]
    assert setting["referenceProperty"] == "iOC"


def test_build_matlab_setting_std_passthrough():
    thr = default_thresholds()
    setting = build_matlab_setting(thr)
    idx = setting["filterProperties"].index("iOC")
    assert setting["thresholdValue"][idx] == "3std"


def test_build_matlab_setting_number_both_uses_lo_hi_pair():
    thr = {"iOC": ThresholdConfig(True, "both", "number", value_lo=1.0, value_hi=5.0)}
    # only iOC enabled; others must be disabled to isolate
    for p in default_thresholds():
        thr.setdefault(p, ThresholdConfig(False, "both", "3std"))
    setting = build_matlab_setting(thr)
    idx = setting["filterProperties"].index("iOC")
    # iOC is a micro prop -> scaled by 1e-6
    assert setting["thresholdValue"][idx] == pytest.approx([1.0e-6, 5.0e-6])


def test_build_matlab_setting_number_one_sided_scalar_and_nonmicro_unscaled():
    thr = {"D": ThresholdConfig(True, "upper", "number", value=2.0)}
    for p in default_thresholds():
        thr.setdefault(p, ThresholdConfig(False, "both", "3std"))
    setting = build_matlab_setting(thr)
    idx = setting["filterProperties"].index("D")
    assert setting["thresholdValue"][idx] == [2.0]  # not scaled (D is not micro)


def test_compute_states_override_precedence():
    not_outlier = np.array([True, False, True])
    overrides = {0: "excluded", 1: "kept"}
    states = compute_states(3, not_outlier, overrides)
    assert states == ["manual-excluded", "manual-kept", "auto-kept"]


def test_thresholds_roundtrip_and_missing_key_gets_default():
    thr = default_thresholds()
    thr["iOC"].value_hi = 9.0
    restored = thresholds_from_jsonable(thresholds_to_jsonable(thr))
    assert restored["iOC"].value_hi == 9.0
    # a persisted dict missing a prop still yields a valid config for it
    partial = thresholds_from_jsonable({"iOC": {"enabled": False, "direction": "both", "tv": "3std"}})
    assert partial["iOC"].enabled is False
    assert "D" in partial and partial["D"].enabled is True


def test_thresholds_from_jsonable_ignores_renamed_key():
    restored = thresholds_from_jsonable({"gone": {"enabled": True, "direction": "both", "tv": "3std"}})
    assert "gone" not in restored
    assert set(restored) == set(default_thresholds())


def test_filter_collection_masks_arrays_and_lists_and_skips_mismatched():
    collection = {
        "iOC": np.array([1.0, 2.0, 3.0]),
        "label": ["a", "b", "c"],
        "unrelated": np.array([1.0, 2.0]),  # wrong length -> skipped
    }
    mask = np.array([True, False, True])
    out = filter_collection(collection, mask)  # type: ignore[arg-type]
    assert out["iOC"] == [1.0, 3.0]
    assert out["label"] == ["a", "c"]
    assert "unrelated" not in out

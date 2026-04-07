"""Ports of std_modified.m, iOCcalibration.m."""

from __future__ import annotations

import numpy as np


def std_modified(
    x: np.ndarray, fun_mean: int = 1, fun_stabil: int = 1
) -> tuple[float, float, np.ndarray]:
    """Returns (STD, MEAN, selected bool array)."""
    x = np.array(x, dtype=float)
    selected = ~(np.isnan(x) | np.isinf(x))

    if fun_mean == 0:
        std_v = np.sqrt(np.sum(x[selected] ** 2) / max(selected.sum() - 1, 1))
        mean_v = 0.0
        if fun_stabil == 1 and selected.sum() > 1:
            sel0 = selected.copy()
            selected = np.abs(x) < 3 * std_v
            while selected.sum() < sel0.sum():
                std_v = np.sqrt(np.sum(x[selected] ** 2) / max(selected.sum() - 1, 1))
                sel0 = selected.copy()
                selected = np.abs(x) < 3 * std_v
    else:
        mean_v = np.nanmean(x[selected])
        std_v = np.sqrt(
            np.sum((x[selected] - mean_v) ** 2) / max(selected.sum() - 1, 1)
        )
        if fun_stabil == 1 and selected.sum() > 1:
            sel0 = selected.copy()
            selected = np.abs(x - mean_v) < 3 * std_v
            while selected.sum() < sel0.sum():
                mean_v = np.nanmean(x[selected])
                std_v = np.sqrt(
                    np.sum((x[selected] - mean_v) ** 2) / max(selected.sum() - 1, 1)
                )
                sel0 = selected.copy()
                selected = np.abs(x - mean_v) < 3 * std_v

    return float(std_v), float(mean_v), selected


def ioc_calibration_core(
    ioc_profiles: list, positions: list, dx: float = 1.0, threshold: float = 1e-3
) -> dict:
    n_traj = len(ioc_profiles)
    pos_start = max(float(p.min()) for p in positions)
    pos_end = min(float(p.max()) for p in positions)

    slices = []
    a = 0
    for p in positions:
        slices.append(slice(a, a + len(p)))
        a += len(p)

    all_pos = np.concatenate([np.array(p, dtype=float) for p in positions])
    all_ioc = np.concatenate([np.array(s, dtype=float) for s in ioc_profiles])

    x = np.arange(pos_start + dx / 2, pos_end - dx / 2 + 1, dx)
    if len(x) == 0:
        x = np.array([(pos_start + pos_end) / 2])

    ind_x = [
        np.where((all_pos >= xi - dx / 2) & (all_pos <= xi + dx / 2))[0] for xi in x
    ]

    not_outlier_frame = (all_pos >= x[0]) & (all_pos <= x[-1])
    not_outlier_frame0 = ~not_outlier_frame.copy()

    Aint = np.ones_like(all_ioc)
    ioc_norm = np.ones_like(all_ioc)
    A = np.zeros(len(x))
    A0 = np.full(len(x), np.inf)
    Astd = np.zeros(len(x))
    AN = np.zeros(len(x))

    for _ in range(100):
        if np.array_equal(not_outlier_frame, not_outlier_frame0) and np.all(
            np.abs(A - A0) <= threshold
        ):
            break
        not_outlier_frame0 = not_outlier_frame.copy()
        A0 = A.copy()

        Y = all_ioc / Aint
        for i in range(n_traj):
            sl = slices[i]
            valid = np.where(not_outlier_frame[sl])[0]
            if not len(valid):
                continue
            mean_ioc = np.nanmean(Y[sl][valid])
            if mean_ioc and not np.isnan(mean_ioc):
                ioc_norm[sl] = all_ioc[sl] / mean_ioc

        _, _, selected = std_modified(
            ioc_norm[not_outlier_frame] / Aint[not_outlier_frame],
            fun_mean=1,
            fun_stabil=1,
        )
        not_outlier_frame[np.where(not_outlier_frame)[0]] = selected

        A_new = np.zeros(len(x))
        Astd = np.zeros(len(x))
        AN = np.zeros(len(x))
        for i, ix in enumerate(ind_x):
            valid = ix[not_outlier_frame[ix]]
            if not len(valid):
                A_new[i] = Astd[i] = np.nan
            else:
                A_new[i] = np.nanmean(ioc_norm[valid])
                Astd[i] = np.nanstd(ioc_norm[valid], ddof=1) if len(valid) > 1 else 0.0
                AN[i] = len(valid)

        A_mean = np.nanmean(A_new)
        A = A_new / A_mean if A_mean and not np.isnan(A_mean) else A_new
        Aint = np.interp(all_pos, x, A)

    return {"x": x.tolist(), "A": A.tolist(), "Astd": Astd.tolist(), "AN": AN.tolist()}


def run_ioc_calibration(collection: dict, keep_mask: np.ndarray) -> tuple[dict, dict]:
    ioc_profiles = collection["iOCprofile"]
    pos_refined = collection["positionRefined"]
    kept_idx = np.where(keep_mask)[0]

    calibration = ioc_calibration_core(
        [ioc_profiles[i] for i in kept_idx],
        [pos_refined[i] for i in kept_idx],
    )

    cal_x, cal_A = np.array(calibration["x"]), np.array(calibration["A"])
    updated = dict(collection)
    new_ioc = np.array(collection["iOC"], dtype=float)
    new_std = np.array(collection["STDiOC"], dtype=float)
    new_N = np.array(collection["N"], dtype=float)

    for i in range(len(collection["iOC"])):
        pos_i = np.array(pos_refined[i], dtype=float)
        ioc_i = np.array(ioc_profiles[i], dtype=float)
        Y = ioc_i / np.interp(pos_i, cal_x, cal_A)
        std_v, mean_v, selected = std_modified(Y, fun_mean=1, fun_stabil=1)
        new_std[i], new_ioc[i], new_N[i] = std_v, mean_v, float(selected.sum())

    updated["iOC"], updated["STDiOC"], updated["N"] = new_ioc, new_std, new_N
    return calibration, updated

"""Ports of analyzePopulation_robustMean.m, std_modified_ND.m, analyzePopulation_gaussFit.m."""

from __future__ import annotations

import numpy as np


def robust_mean(collection: dict, props: list[str]) -> dict:
    arrays = [np.array(collection[p], dtype=float) for p in props]
    Y = np.stack(arrays, axis=0)
    weights = np.array(collection.get("N", []), dtype=float)
    if len(weights) != Y.shape[1]:
        weights = None

    selected = ~np.any(np.isnan(Y), axis=0)
    selected0 = ~selected.copy()
    mean_v = np.full(len(props), np.nan)
    std_v = np.full(len(props), np.nan)

    for _ in range(100):
        if np.array_equal(selected, selected0):
            break
        selected0 = selected.copy()
        Y_sel = Y[:, selected]
        if weights is not None:
            w_sel = weights[selected]
            w_sum = w_sel.sum()
            mean_v = (Y_sel * w_sel).sum(axis=1) / w_sum
            std_v = np.sqrt(
                (w_sel * (Y_sel - mean_v[:, None]) ** 2).sum(axis=1) / w_sum
            )
        else:
            mean_v = Y_sel.mean(axis=1)
            std_v = Y_sel.std(axis=1, ddof=0)

        std_safe = np.where(std_v == 0, 1.0, std_v)
        R = np.sum(
            ((Y[:, selected] - mean_v[:, None]) / (std_safe[:, None] * 3)) ** 2, axis=0
        )
        selected[selected] = R < 1

    result = {}
    for i, prop in enumerate(props):
        fwhm = 2 * np.sqrt(2 * np.log(2)) * std_v[i]
        result[prop] = {
            "MEAN": float(mean_v[i]),
            "STD": float(std_v[i]),
            "FWHM": float(fwhm),
            "RESOLUTION": float(abs(mean_v[i]) / fwhm) if fwhm != 0 else float("nan"),
        }
    return result


def gauss_fit(collection: dict, props: list[str]) -> dict:
    from scipy.optimize import curve_fit

    N_field = collection.get("N")
    result = {}

    for prop in props:
        Y = np.array(collection[prop], dtype=float)
        Y = Y[~np.isnan(Y)]
        mean_est = float(np.median(Y))
        std_est = float(np.median(np.abs(Y - mean_est)) / 0.6745)
        n_est = int(np.sum((Y > mean_est - 3 * std_est) & (Y < mean_est + 3 * std_est)))

        if N_field is not None and len(N_field) == len(collection[prop]):
            Y_expanded = np.repeat(
                np.array(collection[prop], dtype=float), np.array(N_field, dtype=int)
            )
            Y_expanded = Y_expanded[~np.isnan(Y_expanded)]
        else:
            Y_expanded = Y

        dx = 3.5 * std_est / max(n_est ** (1 / 3), 1)
        edges = np.arange(Y_expanded.min() - dx / 2, Y_expanded.max() + dx / 2 + dx, dx)
        counts, _ = np.histogram(Y_expanded, bins=edges)
        centers = (edges[:-1] + edges[1:]) / 2

        def gaussian(x, amp, mu, sig):
            return amp * np.exp(-((x - mu) ** 2) / (2 * sig**2))

        try:
            popt, _ = curve_fit(
                gaussian,
                centers,
                counts.astype(float),
                p0=[
                    float(np.interp(mean_est, centers, counts.astype(float))),
                    mean_est,
                    std_est,
                ],
                maxfev=10000,
            )
            fit_mean, fit_std = float(popt[1]), float(abs(popt[2]))
        except Exception:  # noqa: BLE001
            fit_mean, fit_std = mean_est, std_est

        fwhm = 2 * np.sqrt(2 * np.log(2)) * fit_std
        result[prop] = {
            "MEAN": fit_mean,
            "STD": fit_std,
            "FWHM": fwhm,
            "RESOLUTION": float(abs(fit_mean) / fwhm) if fwhm != 0 else float("nan"),
            "_hist_centers": centers.tolist(),
            "_hist_counts": counts.tolist(),
        }
    return result

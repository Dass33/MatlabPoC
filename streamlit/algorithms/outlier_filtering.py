"""Port of findTrajectoryOutliers.m."""

from __future__ import annotations

import numpy as np

DEFAULT_SIGMA = 6.0


def find_outliers(collection: dict, filt_config: dict, thresholds: dict) -> np.ndarray:
    """Returns bool array: True = not outlier."""
    ref_prop = filt_config.get("referenceProperty", "iOC")
    filter_props = filt_config.get("filterProperties", [])

    ref = np.array(collection.get(ref_prop, []), dtype=float)
    n = len(ref)
    if n == 0:
        return np.ones(0, dtype=bool)

    not_outlier = ~np.isnan(ref)
    for prop in filter_props:
        if prop in collection:
            not_outlier &= ~np.isnan(np.array(collection[prop], dtype=float))

    not_outlier0 = ~not_outlier.copy()
    for _ in range(100):
        if np.array_equal(not_outlier, not_outlier0):
            break
        not_outlier0 = not_outlier.copy()

        per_prop = []
        for prop in filter_props:
            if prop not in collection:
                per_prop.append(np.ones(n, dtype=bool))
                continue

            cfg = thresholds.get(
                prop, {"sigma": DEFAULT_SIGMA, "direction": "upper", "tv": "3std"}
            )
            direction = cfg.get("direction", "upper")
            tv = cfg.get("tv", "3std")
            sigma = float(cfg.get("sigma", DEFAULT_SIGMA))
            y = np.array(collection[prop], dtype=float)

            if tv == "3std":
                y_in = y[not_outlier0]
                mean_v = np.nanmean(y_in)
                std_v = np.nanstd(y_in, ddof=1) if len(y_in) > 1 else 1.0
                lo, hi = mean_v - sigma * std_v, mean_v + sigma * std_v

            elif tv == "3std_conditional":
                y_in, x_in = y[not_outlier0], ref[not_outlier0]
                A = np.column_stack([x_in, np.ones(len(x_in))])
                p, *_ = np.linalg.lstsq(A, y_in, rcond=None)
                fitted = p[0] * ref + p[1]
                ratio = y_in / (p[0] * x_in + p[1])
                mean_r = np.nanmean(ratio)
                std_r = np.nanstd(ratio, ddof=1) if len(ratio) > 1 else 1.0
                lo, hi = (
                    (mean_r - sigma * std_r) * fitted,
                    (mean_r + sigma * std_r) * fitted,
                )

            else:  # "number"
                if direction == "both":
                    lo, hi = (
                        float(cfg.get("value_lo", 0.0)),
                        float(cfg.get("value_hi", 0.0)),
                    )
                elif direction == "lower":
                    lo, hi = float(cfg.get("value", 0.0)), np.inf
                else:
                    lo, hi = -np.inf, float(cfg.get("value", 0.0))

            if direction == "upper":
                lo = -np.inf if np.isscalar(lo) else np.full(n, -np.inf)
            elif direction == "lower":
                hi = np.inf if np.isscalar(hi) else np.full(n, np.inf)

            per_prop.append((y > lo) & (y < hi))

        not_outlier = np.asarray(np.stack(per_prop, axis=0).all(axis=0))

    return not_outlier

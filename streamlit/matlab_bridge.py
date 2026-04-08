"""
Bridge to the compiled MATLAB nsm_algorithms package.

MCR is initialised once per process on first call. All functions communicate
via JSON strings so no MATLAB-specific Python types leak into the rest of
the codebase.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

_pkg = None


def _get_pkg():
    global _pkg
    if _pkg is None:
        import nsm_algorithms  # installed from matlab/Compiled/PythonPackage/nsm_algorithms
        _pkg = nsm_algorithms.initialize()
        log.info("MATLAB MCR initialised")
    return _pkg


# ─── serialisation helpers ───────────────────────────────────────────────────

def _to_json(obj: Any) -> str:
    def _default(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        raise TypeError(type(o))
    return json.dumps(obj, default=_default)


def _from_json(s: Any) -> Any:
    return json.loads(str(s))


def _prep_collection(collection: dict) -> dict:
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


# ─── public API ──────────────────────────────────────────────────────────────

def find_outliers(collection: dict, matlab_setting: dict) -> np.ndarray:
    """
    Call MATLAB findTrajectoryOutliers.

    matlab_setting must have:
        referenceProperty  : str
        filterProperties   : list[str]
        thresholdDirection : list[str]   ('upper' | 'lower' | 'both')
        thresholdValue     : list        ('3std' | '3std_conditional' | [numeric])

    Returns a bool array of length N: True = not an outlier.
    """
    result = _get_pkg().runOutlierFiltering(
        _to_json(_prep_collection(collection)),
        _to_json(matlab_setting),
        nargout=1,
    )
    return np.array(_from_json(result), dtype=bool)


def run_ioc_calibration(
    collection: dict, keep_mask: np.ndarray
) -> tuple[dict, dict]:
    """
    Run iOC calibration on the kept subset, then apply it to all trajectories.

    Returns
    -------
    calibration : dict with keys x, A, Astd, AN
    updated     : dict with keys iOC, STDiOC, N  (all trajectories, recalibrated)
    """
    cal_json, upd_json = _get_pkg().runIocCalibration(
        _to_json(_prep_collection(collection)),
        _to_json(keep_mask.tolist()),
        nargout=2,
    )
    return _from_json(cal_json), _from_json(upd_json)


def run_population_analysis(collection: dict, setting: dict) -> dict:
    """
    Run population analysis.

    setting must have:
        Title      : 'robustMean' | 'gaussFit'
        properties : list[str]

    Returns dict keyed by property name:
        {prop: {MEAN, STD, FWHM, RESOLUTION, [_hist_centers, _hist_counts]}}
    """
    result_json = _get_pkg().runPopulationAnalysis(
        _to_json(collection),
        _to_json(setting),
        nargout=1,
    )
    result = _from_json(result_json)
    # rename histogram fields to the underscore-prefixed convention used in the UI
    for prop_data in result.values():
        if "histCenters" in prop_data:
            prop_data["_hist_centers"] = prop_data.pop("histCenters")
        if "histCounts" in prop_data:
            prop_data["_hist_counts"] = prop_data.pop("histCounts")
    return result

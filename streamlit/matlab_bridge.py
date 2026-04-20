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


def _get_pkg() -> Any:
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


def _prep_collection(collection: dict[str, object]) -> dict[str, object]:
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


def find_outliers(
    collection: dict[str, object], matlab_setting: dict[str, object]
) -> np.ndarray:
    """
    Call MATLAB findTrajectoryOutliers.

    matlab_setting must have:
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


def run_postprocessing(
    collection: dict[str, object],
    matlab_setting: dict[str, object],
    keep_mask: np.ndarray,
    calibration_on: bool = True,
) -> dict[str, object]:
    """
    Call MATLAB runPostprocessing — filter↔calibrate fixed-point loop.

    matlab_setting is the flat outlierFiltering dict (filterProperties, thresholdDirection,
    thresholdValue) as returned by _build_matlab_setting.

    Returns dict with:
        notOutlier  : bool ndarray, full length
        iOC, STDiOC, N : float ndarray, full length (calibrated if calibration_on)
        threshold   : threshold info from MATLAB
        calibration : calibration curve dict (x, A, Astd, AN), or None
    """
    postprocessing_setting = {
        "iOCcalibration": "on" if calibration_on else "off",
        "outlierFiltering": matlab_setting,
    }
    result_json = _get_pkg().runPostprocessing(
        _to_json(_prep_collection(collection)),
        _to_json(postprocessing_setting),
        _to_json(keep_mask.tolist()),
        nargout=1,
    )
    data = _from_json(result_json)
    data["notOutlier"] = np.array(data["notOutlier"], dtype=bool)
    for key in ("iOC", "STDiOC", "N"):
        if key in data:
            data[key] = np.array(data[key], dtype=float)
    if not data.get("calibration"):
        data["calibration"] = None
    return data


def run_population_analysis(
    collection: dict[str, object], setting: dict[str, object]
) -> dict[str, object]:
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

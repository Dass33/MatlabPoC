"""
Bridge to the compiled MATLAB nsm_algorithms package.

MCR is initialised once per process on first call. All functions communicate
via JSON strings.
"""

from __future__ import annotations

import json
import logging
from typing import Any, NotRequired, TypedDict

import numpy as np

import utils as u


class Collection(TypedDict):
    iOC: np.ndarray
    STDiOC: np.ndarray
    N: np.ndarray
    D: np.ndarray
    velocity: np.ndarray
    positionRefined: np.ndarray
    timeFrame: np.ndarray
    iOCprofile: np.ndarray
    positionStart: NotRequired[np.ndarray]
    positionEnd: NotRequired[np.ndarray]
    ExperimentTimeStamp: NotRequired[np.ndarray]


class MatlabFilterSetting(TypedDict):
    filterProperties: list[str]
    thresholdDirection: list[str]
    thresholdValue: list[str | list[float]]
    referenceProperty: str


class PostprocessingResult(TypedDict):
    notOutlier: np.ndarray
    iOC: np.ndarray
    STDiOC: np.ndarray
    N: np.ndarray
    threshold: object
    calibration: dict[str, object] | None


log = logging.getLogger(__name__)

_pkg = None


def _get_pkg() -> Any:
    global _pkg
    if _pkg is None:
        import nsm_algorithms  # type: ignore[import]  # installed from matlab/Compiled/PythonPackage/nsm_algorithms

        _pkg = nsm_algorithms.initialize()
        log.info("MATLAB MCR initialised")
    return _pkg


# ─── public API ──────────────────────────────────────────────────────────────


def find_outliers(
    collection: Collection, matlab_setting: MatlabFilterSetting
) -> np.ndarray:
    """Returns a boolean mask of length N where True means the trajectory is not an outlier."""
    preped_collection = u.to_json(u.prep_collection(collection))
    matlab_setting_json = u.to_json(matlab_setting)

    result = _get_pkg().runOutlierFiltering(
        preped_collection,
        matlab_setting_json,
        nargout=1,
    )
    return np.array(json.loads(str(result)), dtype=bool)


def run_postprocessing(
    collection: Collection,
    matlab_setting: MatlabFilterSetting,
    keep_mask: np.ndarray,
    force_keep: np.ndarray,
    calibration_on: bool = True,
) -> PostprocessingResult:
    """Runs outlier filtering and optional iOC calibration via MATLAB. Returns a PostprocessingResult."""
    postprocessing_setting = {
        "iOCcalibration": "on" if calibration_on else "off",
        "outlierFiltering": matlab_setting,
    }
    preped_collection = u.to_json(u.prep_collection(collection))
    settings_json = u.to_json(postprocessing_setting)
    keep_mask_json = u.to_json(keep_mask.tolist())
    force_keep_json = u.to_json(force_keep.tolist())

    result_json = _get_pkg().runPostprocessing(
        preped_collection,
        settings_json,
        keep_mask_json,
        force_keep_json,
        nargout=1,
    )
    data = json.loads(str(result_json))
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
    """Runs population analysis via MATLAB. Returns statistics keyed by property name (MEAN, STD, FWHM, RESOLUTION, histogram bins/counts)."""
    result_json = _get_pkg().runPopulationAnalysis(
        u.to_json(collection),
        u.to_json(setting),
        nargout=1,
    )
    return json.loads(str(result_json))

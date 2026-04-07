from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import streamlit as st

DEFAULT_CONFIG: dict[str, Any] = {
    "exportOptionalFigures": False,
    "inputDataFormat": "tiff2",
    "Dt": 0.007,
    "Dx": 0.066,
    "flipIntensity": True,
    "flowEstimate": -3.4,
    "kymographPreprocessing": {
        "darkCalibration": 8,
        "Wx": 15,
        "Wt": 50,
        "ws": 2.36,
        "removeBackground": "robustmean",
    },
    "Detection": {"peakSign": "negative", "pfa": 1e-5, "localOptimumRange": 6},
    "tracker": "gabClosingTracker",
    "Tlength": 4,
    "thresholdLimit": -2.0,
    "TmaxNo": 8,
    "Linking": {
        "minTrackLength": 10,
        "cut_off_distance": 20,
        "unmatched_penalty_distance": 15,
        "maxNegativeGab": 2,
        "maxPositiveGab": 3,
        "gab_closing_cut_off_distance": 40,
        "gab_closing_penalty_distance": 30,
    },
    "trajectoryProperties": [
        "positionRefined",
        "timeFrame",
        "iOCprofile",
        "N",
        "iOC",
        "STDiOC",
        "D",
        "velocity",
    ],
    "outlierFiltering": {
        "referenceProperty": "iOC",
        "filterProperties": ["STDiOC", "velocity", "N", "positionStart", "positionEnd"],
        "thresholdDirection": ["upper", "both", "lower", "upper", "lower"],
        "thresholdValue": ["3std", "3std", "3std", "3std", "3std"],
    },
    "populationAnalysis": {
        "Title": "robustMean",
        "properties": ["iOC", "D", "velocity"],
    },
}


def _pick(src: dict, *keys) -> dict:
    return {k: src[k] for k in keys if k in src}


def apply_config_to_session_state(built_config: dict) -> None:
    flat = _pick(
        built_config,
        "Dt",
        "Dx",
        "flipIntensity",
        "flowEstimate",
        "tracker",
        "Tlength",
        "thresholdLimit",
        "TmaxNo",
    )

    pp = built_config.get("kymographPreprocessing", {})
    if "darkCalibration" in pp:
        dc = pp["darkCalibration"]
        if isinstance(dc, str):
            flat.update({"dark_cal_mode": "File path", "dark_cal_path": dc})
        else:
            flat.update({"dark_cal_mode": "Scalar", "darkCalibration": int(dc)})
    if "ws" in pp:
        flat["ws"] = pp["ws"]
    if "Wx" in pp:
        wx = pp["Wx"]
        flat.update(
            {"sweep_enabled": True, "Wx_sweep": ", ".join(str(v) for v in wx)}
            if isinstance(wx, list)
            else {"Wx_single": float(wx)}
        )
    if "Wt" in pp:
        wt = pp["Wt"]
        flat.update(
            {"sweep_enabled": True, "Wt_sweep": ", ".join(str(v) for v in wt)}
            if isinstance(wt, list)
            else {"Wt_single": float(wt)}
        )

    flat.update(
        _pick(built_config.get("Detection", {}), "peakSign", "pfa", "localOptimumRange")
    )
    flat.update(
        _pick(
            built_config.get("Linking", {}),
            "minTrackLength",
            "cut_off_distance",
            "unmatched_penalty_distance",
            "maxNegativeGab",
            "maxPositiveGab",
            "gab_closing_cut_off_distance",
            "gab_closing_penalty_distance",
        )
    )
    st.session_state.update(flat)


def render_config_sidebar() -> dict:
    DC = DEFAULT_CONFIG

    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("Save / Load config"):
        uploaded = st.file_uploader(
            "Load config JSON", type=["json"], key="built_config_upload"
        )
        if uploaded:
            try:
                loaded = json.load(uploaded)
                st.session_state["_loaded_config"] = loaded
                apply_config_to_session_state(loaded)
                st.success("Config loaded.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not load config: {e}")

    with st.sidebar.expander("Acquisition", expanded=False):
        Dt = st.number_input(
            "Dt (frame duration, s)",
            value=DC["Dt"],
            format="%.4f",
            step=0.001,
            key="Dt",
        )
        Dx = st.number_input(
            "Dx (pixel size, μm)", value=DC["Dx"], format="%.4f", step=0.001, key="Dx"
        )
        flipIntensity = st.checkbox(
            "Flip intensity", value=DC["flipIntensity"], key="flipIntensity"
        )
        flowEstimate = st.number_input(
            "Flow estimate (px/frame)",
            value=DC["flowEstimate"],
            format="%.2f",
            step=0.1,
            key="flowEstimate",
        )

    with st.sidebar.expander("Preprocessing"):
        dark_cal_mode = st.radio(
            "Dark calibration source", ["Scalar", "Template"], key="dark_cal_mode"
        )
        if dark_cal_mode == "Scalar":
            darkCalibration: int | str = st.number_input(
                "Dark calibration value", value=8, step=1, key="darkCalibration"
            )
        else:
            dark_cal_template = st.selectbox(
                "Dark calibration .mat template",
                ["some", "different", "templates"],
                index=0,
                key="dark_cal_template",
            )
            dark_calibration_path = (
                Path(__file__).parent / "templates" / f"{dark_cal_template}.mat"
            )
            st.session_state["dark_cal_bytes"] = dark_calibration_path.read_bytes()
            darkCalibration = str(dark_calibration_path)
        Wx = st.number_input(
            "Wx (spatial window, px)",
            value=float(DC["kymographPreprocessing"]["Wx"]),
            step=1.0,
            key="Wx_single",
        )
        Wt = st.number_input(
            "Wt (temporal window, frames)",
            value=float(DC["kymographPreprocessing"]["Wt"]),
            step=1.0,
            key="Wt_single",
        )
        ws = st.number_input(
            "ws (PSF width, px)",
            value=DC["kymographPreprocessing"]["ws"],
            format="%.2f",
            step=0.01,
            key="ws",
        )
        remove_background_mode = st.selectbox(
            "Remove background mode",
            ["movmedian", "movmean"],
            index=0,
            key="remove_background_mode",
        )

    with st.sidebar.expander("Detection"):
        peakSign = st.selectbox(
            "Peak sign",
            ["negative", "positive", "negative-positive"],
            index=0,
            key="peakSign",
        )
        pfa = st.number_input(
            "pfa", value=DC["Detection"]["pfa"], format="%.e", key="pfa"
        )
        localOptimumRange = st.number_input(
            "Local optimum range",
            value=int(DC["Detection"]["localOptimumRange"]),
            step=1,
            key="localOptimumRange",
        )

    with st.sidebar.expander("Tracking"):
        tracker = st.selectbox(
            "Tracker algorithm",
            ["gabClosingTracker", "trackBeforeDetect"],
            index=0,
            key="tracker",
        )
        minTrackLength = st.number_input(
            "Min track length",
            value=int(DC["Linking"]["minTrackLength"]),
            step=1,
            key="minTrackLength",
        )
        cut_off_distance = st.number_input(
            "Cut-off distance",
            value=float(DC["Linking"]["cut_off_distance"]),
            step=1.0,
            key="cut_off_distance",
        )
        unmatched_penalty_distance = st.number_input(
            "Unmatched penalty distance",
            value=float(DC["Linking"]["unmatched_penalty_distance"]),
            step=1.0,
            key="unmatched_penalty_distance",
        )

        if tracker == "gabClosingTracker":
            maxNegativeGab = st.number_input(
                "Max negative gap",
                value=int(DC["Linking"]["maxNegativeGab"]),
                step=1,
                key="maxNegativeGab",
            )
            maxPositiveGab = st.number_input(
                "Max positive gap",
                value=int(DC["Linking"]["maxPositiveGab"]),
                step=1,
                key="maxPositiveGab",
            )
            gab_closing_cut_off_distance = st.number_input(
                "Gap closing cut-off distance",
                value=float(DC["Linking"]["gab_closing_cut_off_distance"]),
                step=1.0,
                key="gab_closing_cut_off_distance",
            )
            gab_closing_penalty_distance = st.number_input(
                "Gap closing penalty distance",
                value=float(DC["Linking"]["gab_closing_penalty_distance"]),
                step=1.0,
                key="gab_closing_penalty_distance",
            )
            Tlength, thresholdLimit, TmaxNo = (
                DC["Tlength"],
                DC["thresholdLimit"],
                DC["TmaxNo"],
            )
        else:
            maxNegativeGab = DC["Linking"]["maxNegativeGab"]
            maxPositiveGab = DC["Linking"]["maxPositiveGab"]
            gab_closing_cut_off_distance = DC["Linking"]["gab_closing_cut_off_distance"]
            gab_closing_penalty_distance = DC["Linking"]["gab_closing_penalty_distance"]
            _tlengths = [2, 4, 8, 16, 32, 64]
            Tlength = st.selectbox(
                "Track length (Tlength)",
                _tlengths,
                index=_tlengths.index(DC["Tlength"]),
                key="Tlength",
            )
            thresholdLimit = st.number_input(
                "Intensity threshold limit",
                value=float(DC["thresholdLimit"]),
                step=0.5,
                key="thresholdLimit",
            )
            TmaxNo = st.number_input(
                "Max associations per DIPS (TmaxNo)",
                value=int(DC["TmaxNo"]),
                step=1,
                key="TmaxNo",
            )

    exportOptionalFigures = st.sidebar.checkbox("Export optional figures")

    config = copy.deepcopy(st.session_state.get("_loaded_config", DC))
    config.update({
        "exportOptionalFigures": exportOptionalFigures,
        "Dt": Dt,
        "Dx": Dx,
        "flipIntensity": flipIntensity,
        "flowEstimate": flowEstimate,
        "kymographPreprocessing": {
            "darkCalibration": darkCalibration
            if isinstance(darkCalibration, str)
            else int(darkCalibration),
            "Wx": Wx if isinstance(Wx, list) else float(Wx),
            "Wt": Wt if isinstance(Wt, list) else float(Wt),
            "ws": float(ws),
            "removeBackground": remove_background_mode,
        },
        "Detection": {
            "peakSign": peakSign,
            "pfa": float(pfa),
            "localOptimumRange": int(localOptimumRange),
        },
        "tracker": tracker,
        "Linking": {
            "minTrackLength": int(minTrackLength),
            "cut_off_distance": float(cut_off_distance),
            "unmatched_penalty_distance": float(unmatched_penalty_distance),
            "maxNegativeGab": int(maxNegativeGab),
            "maxPositiveGab": int(maxPositiveGab),
            "gab_closing_cut_off_distance": float(gab_closing_cut_off_distance),
            "gab_closing_penalty_distance": float(gab_closing_penalty_distance),
        },
        "Tlength": int(Tlength),
        "thresholdLimit": float(thresholdLimit),
        "TmaxNo": int(TmaxNo),
    })

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(config, indent=2),
        file_name="config.json",
        mime="application/json",
        width="stretch",
    )

    return config

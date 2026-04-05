from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import streamlit as st

DEFAULT_CONFIG: dict[str, Any] = {
    "exportOptionalFigures": False,
    # Acquisition
    "inputDataFormat": "tiff2",
    "Dt": 0.007,
    "Dx": 0.066,
    "flipIntensity": True,
    "flowEstimate": -3.4,
    # Preprocessing
    "kymographPreprocessing": {
        "darkCalibration": 8,
        "Wx": 15,
        "Wt": 50,
        "ws": 2.36,
        "removeBackground": "robustmean",
    },
    # Detection
    "Detection": {"peakSign": "negative", "pfa": 1e-5, "localOptimumRange": 6},
    # Tracker algorithm
    "tracker": "gabClosingTracker",
    # trackBeforeDetect-specific params (ignored when using gabClosingTracker)
    "Tlength": 4,
    "thresholdLimit": -2.0,
    "TmaxNo": 8,
    # Linking
    "Linking": {
        "minTrackLength": 10,
        "cut_off_distance": 20,
        "unmatched_penalty_distance": 15,
        "maxNegativeGab": 2,
        "maxPositiveGab": 3,
        "gab_closing_cut_off_distance": 40,
        "gab_closing_penalty_distance": 30,
    },
    # Trajectory properties to compute (positionStart/positionEnd always added separately)
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
        # filterProperties, thresholdDirection, thresholdValue must always be the same length
        "filterProperties": ["STDiOC", "velocity", "N", "positionStart", "positionEnd"],
        "thresholdDirection": ["upper", "both", "lower", "upper", "lower"],
        "thresholdValue": ["3std", "3std", "3std", "3std", "3std"],
    },
    # Population analysis
    "populationAnalysis": {
        "Title": "robustMean",
        "properties": ["iOC", "D", "velocity"],
    },
}


def apply_config_to_session_state(built_config: dict) -> None:
    flat: dict = {}

    for k in ("Dt", "Dx", "flipIntensity", "flowEstimate"):
        if k in built_config:
            flat[k] = built_config[k]

    pp = built_config.get("kymographPreprocessing", {})
    if "darkCalibration" in pp:
        dc = pp["darkCalibration"]
        if isinstance(dc, str):
            flat["dark_cal_mode"] = "File path"
            flat["dark_cal_path"] = dc
        else:
            flat["dark_cal_mode"] = "Scalar"
            flat["darkCalibration"] = int(dc)
    if "ws" in pp:
        flat["ws"] = pp["ws"]
    if "Wx" in pp:
        wx = pp["Wx"]
        if isinstance(wx, list):
            flat["sweep_enabled"] = True
            flat["Wx_sweep"] = ", ".join(str(v) for v in wx)
        else:
            flat["Wx_single"] = float(wx)
    if "Wt" in pp:
        wt = pp["Wt"]
        if isinstance(wt, list):
            flat["sweep_enabled"] = True
            flat["Wt_sweep"] = ", ".join(str(v) for v in wt)
        else:
            flat["Wt_single"] = float(wt)

    det = built_config.get("Detection", {})
    for k in ("peakSign", "pfa", "localOptimumRange"):
        if k in det:
            flat[k] = det[k]

    if "tracker" in built_config:
        flat["tracker"] = built_config["tracker"]
    for k in ("Tlength", "thresholdLimit", "TmaxNo"):
        if k in built_config:
            flat[k] = built_config[k]

    link = built_config.get("Linking", {})
    for k in (
        "minTrackLength",
        "cut_off_distance",
        "unmatched_penalty_distance",
        "maxNegativeGab",
        "maxPositiveGab",
        "gab_closing_cut_off_distance",
        "gab_closing_penalty_distance",
    ):
        if k in link:
            flat[k] = link[k]

    for k, v in flat.items():
        st.session_state[k] = v


def render_config_sidebar() -> dict:
    built_config = DEFAULT_CONFIG

    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("Save / Load config"):
        uploaded_built_config = st.file_uploader(
            "Load config JSON", type=["json"], key="built_config_upload"
        )
        if uploaded_built_config:
            try:
                loaded = json.load(uploaded_built_config)
                st.session_state["_loaded_config"] = loaded
                apply_config_to_session_state(loaded)
                st.success("Config loaded.")
            except Exception as e:  # noqa: BLE001
                st.error(f"Could not load config: {e}")

    # ── Acquisition ──────────────────────────────────────────────────────
    with st.sidebar.expander("Acquisition", expanded=False):
        Dt = st.number_input(
            "Dt (frame duration, s)",
            value=built_config["Dt"],
            format="%.4f",
            step=0.001,
            key="Dt",
        )
        Dx = st.number_input(
            "Dx (pixel size, μm)",
            value=built_config["Dx"],
            format="%.4f",
            step=0.001,
            key="Dx",
        )
        flipIntensity = st.checkbox(
            "Flip intensity", value=built_config["flipIntensity"], key="flipIntensity"
        )
        flowEstimate = st.number_input(
            "Flow estimate (px/frame)",
            value=built_config["flowEstimate"],
            format="%.2f",
            step=0.1,
            key="flowEstimate",
        )

    # ── Preprocessing ────────────────────────────────────────────────────
    with st.sidebar.expander("Preprocessing"):
        dark_cal_mode = st.radio(
            "Dark calibration source",
            options=["Scalar", "Template"],
            key="dark_cal_mode",
        )
        if dark_cal_mode == "Scalar":
            darkCalibration: int | str = st.number_input(
                "Dark calibration value",
                value=8,
                step=1,
                key="darkCalibration",
            )
        else:
            dark_cal_template = st.selectbox(
                "Dark calibration .mat template",
                options=["some", "different", "templates"],
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
            value=float(built_config["kymographPreprocessing"]["Wx"]),
            step=1.0,
            key="Wx_single",
        )
        Wt = st.number_input(
            "Wt (temporal window, frames)",
            value=float(built_config["kymographPreprocessing"]["Wt"]),
            step=1.0,
            key="Wt_single",
        )
        ws = st.number_input(
            "ws (PSF width, px)",
            value=built_config["kymographPreprocessing"]["ws"],
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

    # ── Detection ────────────────────────────────────────────────────────
    with st.sidebar.expander("Detection"):
        peakSign = st.selectbox(
            "Peak sign",
            ["negative", "positive", "negative-positive"],
            index=0,
            key="peakSign",
        )
        pfa = st.number_input(
            "pfa", value=built_config["Detection"]["pfa"], format="%.e", key="pfa"
        )
        localOptimumRange = st.number_input(
            "Local optimum range",
            value=int(built_config["Detection"]["localOptimumRange"]),
            step=1,
            key="localOptimumRange",
        )

    # ── Tracking ─────────────────────────────────────────────────────────
    with st.sidebar.expander("Tracking"):
        _tracker_options = ["gabClosingTracker", "trackBeforeDetect"]
        _tracker_default = built_config.get("tracker", "gabClosingTracker")
        tracker = st.selectbox(
            "Tracker algorithm",
            _tracker_options,
            index=_tracker_options.index(_tracker_default),
            key="tracker",
        )
        minTrackLength = st.number_input(
            "Min track length",
            value=int(built_config["Linking"]["minTrackLength"]),
            step=1,
            key="minTrackLength",
        )
        cut_off_distance = st.number_input(
            "Cut-off distance",
            value=float(built_config["Linking"]["cut_off_distance"]),
            step=1.0,
            key="cut_off_distance",
        )
        unmatched_penalty_distance = st.number_input(
            "Unmatched penalty distance",
            value=float(built_config["Linking"]["unmatched_penalty_distance"]),
            step=1.0,
            key="unmatched_penalty_distance",
        )
        if tracker == "gabClosingTracker":
            maxNegativeGab = st.number_input(
                "Max negative gap",
                value=int(built_config["Linking"]["maxNegativeGab"]),
                step=1,
                key="maxNegativeGab",
            )
            maxPositiveGab = st.number_input(
                "Max positive gap",
                value=int(built_config["Linking"]["maxPositiveGab"]),
                step=1,
                key="maxPositiveGab",
            )
            gab_closing_cut_off_distance = st.number_input(
                "Gap closing cut-off distance",
                value=float(built_config["Linking"]["gab_closing_cut_off_distance"]),
                step=1.0,
                key="gab_closing_cut_off_distance",
            )
            gab_closing_penalty_distance = st.number_input(
                "Gap closing penalty distance",
                value=float(built_config["Linking"]["gab_closing_penalty_distance"]),
                step=1.0,
                key="gab_closing_penalty_distance",
            )
            Tlength = built_config["Tlength"]
            thresholdLimit = built_config["thresholdLimit"]
            TmaxNo = built_config["TmaxNo"]
        else:
            maxNegativeGab = built_config["Linking"]["maxNegativeGab"]
            maxPositiveGab = built_config["Linking"]["maxPositiveGab"]
            gab_closing_cut_off_distance = built_config["Linking"][
                "gab_closing_cut_off_distance"
            ]
            gab_closing_penalty_distance = built_config["Linking"][
                "gab_closing_penalty_distance"
            ]
            Tlength = st.selectbox(
                "Track length (Tlength)",
                [2, 4, 8, 16, 32, 64],
                index=[2, 4, 8, 16, 32, 64].index(built_config["Tlength"]),
                key="Tlength",
            )
            thresholdLimit = st.number_input(
                "Intensity threshold limit",
                value=float(built_config["thresholdLimit"]),
                step=0.5,
                key="thresholdLimit",
            )
            TmaxNo = st.number_input(
                "Max associations per DIPS (TmaxNo)",
                value=int(built_config["TmaxNo"]),
                step=1,
                key="TmaxNo",
            )

    exportOptionalFigures = st.sidebar.checkbox(
        label="Export optional figures",
    )

    # ── Build cofig ───────────────────────────────────────────────────────
    built_config = copy.deepcopy(st.session_state.get("_loaded_config", DEFAULT_CONFIG))
    built_config["exportOptionalFigures"] = exportOptionalFigures
    built_config["Dt"] = Dt
    built_config["Dx"] = Dx
    built_config["flipIntensity"] = flipIntensity
    built_config["flowEstimate"] = flowEstimate
    built_config["kymographPreprocessing"] = {
        "darkCalibration": darkCalibration
        if isinstance(darkCalibration, str)
        else int(darkCalibration),
        "Wx": Wx if isinstance(Wx, list) else float(Wx),
        "Wt": Wt if isinstance(Wt, list) else float(Wt),
        "ws": float(ws),
        "removeBackground": remove_background_mode,
    }

    built_config["Detection"] = {
        "peakSign": peakSign,
        "pfa": float(pfa),
        "localOptimumRange": int(localOptimumRange),
    }

    built_config["tracker"] = tracker
    built_config["Linking"] = {
        "minTrackLength": int(minTrackLength),
        "cut_off_distance": float(cut_off_distance),
        "unmatched_penalty_distance": float(unmatched_penalty_distance),
        "maxNegativeGab": int(maxNegativeGab),
        "maxPositiveGab": int(maxPositiveGab),
        "gab_closing_cut_off_distance": float(gab_closing_cut_off_distance),
        "gab_closing_penalty_distance": float(gab_closing_penalty_distance),
    }

    built_config["Tlength"] = int(Tlength)
    built_config["thresholdLimit"] = float(thresholdLimit)
    built_config["TmaxNo"] = int(TmaxNo)

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(built_config, indent=2),
        file_name="config.json",
        mime="application/json",
        width="stretch",
    )

    return built_config

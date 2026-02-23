from __future__ import annotations

import json
from typing import Any

import streamlit as st

DEFAULT_CONFIG: dict[str, Any] = {
    # Acquisition
    "Dt": 0.007,
    "Dx": 0.066,
    "flipIntensity": True,
    "flowEstimate": -3.4,
    # Preprocessing
    "kymographPreprocessing": {"darkCalibration": 8, "Wx": 15, "Wt": 50, "ws": 2.36},
    # Detection
    "Detection": {"peakSign": "negative", "pfa": 1e-5, "localOptimumRange": 6},
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
        "positionRefined", "timeFrame", "iOCprofile", "N",
        "iOC", "STDiOC", "D", "velocity",
    ],
    # Post-processing
    "iOCcalibration": "on",
    "outlierFiltering": {
        "referenceProperty": "iOC",
        "filterProperties": ["STDiOC", "velocity", "N", "positionStart", "positionEnd"],
        "thresholdDirection": ["upper", "both", "lower", "upper", "lower"],
        "thresholdValue": ["3std", "3std", "3std", "3std", "3std"],
    },
    # Population analysis
    "populationAnalysis": {"Title": "robustMean", "properties": ["iOC", "D", "velocity"]},
}


def _parse_sweep_values(s: str) -> list[float]:
    try:
        return [float(v.strip()) for v in s.split(",") if v.strip()]
    except ValueError:
        st.warning(f"Could not parse sweep values from {s!r} — using default [15.0].")
        return [15.0]


def _build_config(
    Dt, Dx, flipIntensity, flowEstimate,
    darkCalibration, Wx, Wt, ws,
    peakSign, pfa, localOptimumRange,
    minTrackLength, cut_off_distance, unmatched_penalty_distance,
    maxNegativeGab, maxPositiveGab,
    gab_closing_cut_off_distance, gab_closing_penalty_distance,
    iOCcalibration, pop_method,
) -> dict:
    cfg = DEFAULT_CONFIG.copy()
    cfg["Dt"] = Dt
    cfg["Dx"] = Dx
    cfg["flipIntensity"] = flipIntensity
    cfg["flowEstimate"] = flowEstimate
    cfg["kymographPreprocessing"] = {
        "darkCalibration": int(darkCalibration),
        "Wx": Wx if isinstance(Wx, list) else float(Wx),
        "Wt": Wt if isinstance(Wt, list) else float(Wt),
        "ws": float(ws),
    }
    cfg["Detection"] = {
        "peakSign": peakSign,
        "pfa": float(pfa),
        "localOptimumRange": int(localOptimumRange),
    }
    cfg["Linking"] = {
        "minTrackLength": int(minTrackLength),
        "cut_off_distance": float(cut_off_distance),
        "unmatched_penalty_distance": float(unmatched_penalty_distance),
        "maxNegativeGab": int(maxNegativeGab),
        "maxPositiveGab": int(maxPositiveGab),
        "gab_closing_cut_off_distance": float(gab_closing_cut_off_distance),
        "gab_closing_penalty_distance": float(gab_closing_penalty_distance),
    }
    cfg["iOCcalibration"] = iOCcalibration
    cfg["populationAnalysis"]["Title"] = pop_method
    return cfg


def render_config_sidebar() -> dict:
    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("Save / Load config"):
        uploaded_cfg = st.file_uploader(
            "Load config JSON", type=["json"], key="cfg_upload"
        )
        if uploaded_cfg:
            try:
                loaded = json.load(uploaded_cfg)
                for k, v in loaded.items():
                    if k in st.session_state:
                        st.session_state[k] = v
                st.success("Config loaded.")
            except Exception as e:
                st.error(f"Could not load config: {e}")

    cfg = DEFAULT_CONFIG

    # ── Acquisition ──────────────────────────────────────────────────────
    with st.sidebar.expander("Acquisition", expanded=True):
        Dt = st.number_input("Dt (frame duration, s)", value=cfg["Dt"],
                             format="%.4f", step=0.001, key="Dt")
        Dx = st.number_input("Dx (pixel size, μm)", value=cfg["Dx"],
                             format="%.4f", step=0.001, key="Dx")
        flipIntensity = st.checkbox("Flip intensity", value=cfg["flipIntensity"],
                                    key="flipIntensity")
        flowEstimate = st.number_input("Flow estimate (px/frame)",
                                       value=cfg["flowEstimate"],
                                       format="%.2f", step=0.1, key="flowEstimate")

    # ── Preprocessing ────────────────────────────────────────────────────
    with st.sidebar.expander("Preprocessing"):
        darkCalibration = st.number_input("Dark calibration",
                                          value=int(cfg["kymographPreprocessing"]["darkCalibration"]),
                                          step=1, key="darkCalibration")
        Wx_sweep_enabled = st.session_state.get("sweep_enabled", False)
        if Wx_sweep_enabled:
            Wx_str = st.text_input("Wx values (comma-separated, px)",
                                   value=str(cfg["kymographPreprocessing"]["Wx"]),
                                   key="Wx_sweep")
            Wt_str = st.text_input("Wt values (comma-separated, frames)",
                                   value=str(cfg["kymographPreprocessing"]["Wt"]),
                                   key="Wt_sweep")
            Wx = _parse_sweep_values(Wx_str)
            Wt = _parse_sweep_values(Wt_str)
            if len(Wx) > 1 or len(Wt) > 1:
                n_sweeps = len(Wx) * len(Wt)
                st.caption(f"{len(Wx)} × {len(Wt)} = {n_sweeps} sweep(s) will run.")
        else:
            Wx = st.number_input("Wx (spatial window, px)",
                                 value=float(cfg["kymographPreprocessing"]["Wx"]),
                                 step=1.0, key="Wx_single")
            Wt = st.number_input("Wt (temporal window, frames)",
                                 value=float(cfg["kymographPreprocessing"]["Wt"]),
                                 step=1.0, key="Wt_single")
        ws = st.number_input("ws (PSF width, px)",
                             value=cfg["kymographPreprocessing"]["ws"],
                             format="%.2f", step=0.01, key="ws")

    # ── Detection ────────────────────────────────────────────────────────
    with st.sidebar.expander("Detection"):
        peakSign = st.selectbox("Peak sign",
                                ["negative", "positive", "negative-positive"],
                                index=0, key="peakSign")
        pfa = st.number_input("pfa", value=cfg["Detection"]["pfa"],
                              format="%.e", key="pfa")
        localOptimumRange = st.number_input("Local optimum range",
                                            value=int(cfg["Detection"]["localOptimumRange"]),
                                            step=1, key="localOptimumRange")

    # ── Tracking ─────────────────────────────────────────────────────────
    with st.sidebar.expander("Tracking"):
        minTrackLength = st.number_input("Min track length",
                                         value=int(cfg["Linking"]["minTrackLength"]),
                                         step=1, key="minTrackLength")
        cut_off_distance = st.number_input("Cut-off distance",
                                           value=float(cfg["Linking"]["cut_off_distance"]),
                                           step=1.0, key="cut_off_distance")
        unmatched_penalty_distance = st.number_input("Unmatched penalty distance",
                                                     value=float(cfg["Linking"]["unmatched_penalty_distance"]),
                                                     step=1.0, key="unmatched_penalty_distance")
        maxNegativeGab = st.number_input("Max negative gap",
                                         value=int(cfg["Linking"]["maxNegativeGab"]),
                                         step=1, key="maxNegativeGab")
        maxPositiveGab = st.number_input("Max positive gap",
                                         value=int(cfg["Linking"]["maxPositiveGab"]),
                                         step=1, key="maxPositiveGab")
        gab_closing_cut_off_distance = st.number_input("Gap closing cut-off distance",
                                                       value=float(cfg["Linking"]["gab_closing_cut_off_distance"]),
                                                       step=1.0, key="gab_closing_cut_off_distance")
        gab_closing_penalty_distance = st.number_input("Gap closing penalty distance",
                                                       value=float(cfg["Linking"]["gab_closing_penalty_distance"]),
                                                       step=1.0, key="gab_closing_penalty_distance")

    # ── Post-processing ──────────────────────────────────────────────────
    with st.sidebar.expander("Post-processing"):
        ioc_cal_on = st.toggle("iOC calibration", value=(cfg["iOCcalibration"] == "on"),
                               key="iOCcalibration_toggle")
        iOCcalibration = "on" if ioc_cal_on else "off"
        st.caption("Outlier filtering properties and thresholds use defaults (upload config JSON for full control).")

    # ── Population analysis ──────────────────────────────────────────────
    with st.sidebar.expander("Population analysis"):
        pop_method = st.selectbox("Method", ["robustMean", "GMM"],
                                  index=0, key="pop_method")

    # ── Parameter sweep ──────────────────────────────────────────────────
    with st.sidebar.expander("Parameter sweep", expanded=False):
        sweep_enabled = st.checkbox("Enable sweep (Wx × Wt)", value=False,
                                    key="sweep_enabled")

    built_config = _build_config(
        Dt, Dx, flipIntensity, flowEstimate,
        darkCalibration, Wx, Wt, ws,
        peakSign, pfa, localOptimumRange,
        minTrackLength, cut_off_distance, unmatched_penalty_distance,
        maxNegativeGab, maxPositiveGab,
        gab_closing_cut_off_distance, gab_closing_penalty_distance,
        iOCcalibration, pop_method,
    )

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(built_config, indent=2),
        file_name="config.json",
        mime="application/json",
        use_container_width=True,
    )

    return built_config

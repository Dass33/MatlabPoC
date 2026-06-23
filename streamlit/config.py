from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import streamlit as st


@dataclass
class KymographPreprocessing:
    darkCalibration: float | str = 8
    Wx: float = 15.0
    Wt: float = 50.0
    ws: float = 2.36
    removeBackground: str = "movmedian"


@dataclass
class Detection:
    peakSign: str = "negative"
    pfa: float = 1e-5
    localOptimumRange: int = 6


@dataclass
class Linking:
    minTrackLength: int = 10
    cut_off_distance: float = 20.0
    unmatched_penalty_distance: float = 15.0
    maxNegativeGab: int = 2
    maxPositiveGab: int = 3
    gab_closing_cut_off_distance: float = 40.0
    gab_closing_penalty_distance: float = 30.0


@dataclass
class Config:
    exportOptionalFigures: bool = False
    inputDataFormat: str = "tiff2"
    Dt: float = 0.007
    Dx: float = 0.066
    flipIntensity: bool = True
    flowEstimate: float = -3.4
    kymographPreprocessing: KymographPreprocessing = field(
        default_factory=KymographPreprocessing
    )
    Detection: Detection = field(default_factory=Detection)
    tracker: str = "gabClosingTracker"
    Tlength: int = 4
    thresholdLimit: float = -2.0
    TmaxNo: int = 8
    Linking: Linking = field(default_factory=Linking)
    trajectoryProperties: list[str] = field(
        default_factory=lambda: [
            "positionRefined",
            "timeFrame",
            "iOCprofile",
            "N",
            "iOC",
            "STDiOC",
            "D",
            "velocity",
        ]
    )


def render_config_sidebar() -> dict:
    """Sidebar UI for algorithm parameters. Returns a MATLAB-ready config dict."""
    cfg = Config()

    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("Save / Load config"):
        uploaded = st.file_uploader(
            "Load config JSON", type=["json"], key="built_config_upload"
        )
        if uploaded:
            try:
                _apply_config(json.load(uploaded))
                st.success("Config loaded.")
            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON in config file: {e}")
            except (KeyError, TypeError, ValueError) as e:
                st.error(f"Config format error: {e}")

    with st.sidebar.expander("Acquisition", expanded=False):
        cfg.Dt = st.number_input(
            "Dt (frame duration, s)", value=cfg.Dt, format="%.4f", step=0.001, key="Dt"
        )
        cfg.Dx = st.number_input(
            "Dx (pixel size, μm)", value=cfg.Dx, format="%.4f", step=0.001, key="Dx"
        )
        cfg.flipIntensity = st.checkbox(
            "Flip intensity", value=cfg.flipIntensity, key="flipIntensity"
        )
        cfg.flowEstimate = st.number_input(
            "Flow estimate (px/frame)",
            value=cfg.flowEstimate,
            format="%.2f",
            step=0.1,
            key="flowEstimate",
        )

    pp = cfg.kymographPreprocessing
    with st.sidebar.expander("Preprocessing"):
        dark_cal_mode = st.radio(
            "Dark calibration source", ["Scalar", "Template"], key="dark_cal_mode"
        )
        if dark_cal_mode == "Scalar":
            pp.darkCalibration = int(
                st.number_input(
                    "Dark calibration value",
                    value=float(pp.darkCalibration)
                    if not isinstance(pp.darkCalibration, str)
                    else 8.0,
                    step=1.0,
                    key="darkCalibration",
                )
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
            pp.darkCalibration = str(dark_calibration_path)
        pp.Wx = st.number_input(
            "Wx (spatial window, px)", value=pp.Wx, step=1.0, key="Wx"
        )
        pp.Wt = st.number_input(
            "Wt (temporal window, frames)", value=pp.Wt, step=1.0, key="Wt"
        )
        pp.ws = st.number_input(
            "ws (PSF width, px)", value=pp.ws, format="%.2f", step=0.01, key="ws"
        )
        pp.removeBackground = st.selectbox(
            "Remove background mode", ["movmedian", "movmean"], key="removeBackground"
        )

    det = cfg.Detection
    with st.sidebar.expander("Detection"):
        det.peakSign = st.selectbox(
            "Peak sign", ["negative", "positive", "negative-positive"], key="peakSign"
        )
        det.pfa = st.number_input("pfa", value=det.pfa, format="%.e", key="pfa")
        det.localOptimumRange = st.number_input(
            "Local optimum range",
            value=det.localOptimumRange,
            step=1,
            key="localOptimumRange",
        )

    lnk = cfg.Linking
    with st.sidebar.expander("Tracking"):
        cfg.tracker = st.selectbox(
            "Tracker algorithm",
            ["gabClosingTracker", "trackBeforeDetect"],
            key="tracker",
        )
        lnk.minTrackLength = st.number_input(
            "Min track length", value=lnk.minTrackLength, step=1, key="minTrackLength"
        )
        lnk.cut_off_distance = st.number_input(
            "Cut-off distance",
            value=lnk.cut_off_distance,
            step=1.0,
            key="cut_off_distance",
        )
        lnk.unmatched_penalty_distance = st.number_input(
            "Unmatched penalty distance",
            value=lnk.unmatched_penalty_distance,
            step=1.0,
            key="unmatched_penalty_distance",
        )

        if cfg.tracker == "gabClosingTracker":
            lnk.maxNegativeGab = st.number_input(
                "Max negative gap",
                value=lnk.maxNegativeGab,
                step=1,
                key="maxNegativeGab",
            )
            lnk.maxPositiveGab = st.number_input(
                "Max positive gap",
                value=lnk.maxPositiveGab,
                step=1,
                key="maxPositiveGab",
            )
            lnk.gab_closing_cut_off_distance = st.number_input(
                "Gap closing cut-off distance",
                value=lnk.gab_closing_cut_off_distance,
                step=1.0,
                key="gab_closing_cut_off_distance",
            )
            lnk.gab_closing_penalty_distance = st.number_input(
                "Gap closing penalty distance",
                value=lnk.gab_closing_penalty_distance,
                step=1.0,
                key="gab_closing_penalty_distance",
            )
        else:
            _tlengths = [2, 4, 8, 16, 32, 64]
            cfg.Tlength = st.selectbox(
                "Track length (Tlength)",
                _tlengths,
                index=_tlengths.index(cfg.Tlength),
                key="Tlength",
            )
            cfg.thresholdLimit = st.number_input(
                "Intensity threshold limit",
                value=cfg.thresholdLimit,
                step=0.5,
                key="thresholdLimit",
            )
            cfg.TmaxNo = st.number_input(
                "Max associations per DIPS (TmaxNo)",
                value=cfg.TmaxNo,
                step=1,
                key="TmaxNo",
            )

    cfg.exportOptionalFigures = st.sidebar.checkbox(
        "Export optional figures", key="exportOptionalFigures"
    )

    result = asdict(cfg)

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(result, indent=2),
        file_name="config.json",
        mime="application/json",
        width="stretch",
    )

    return result


def _apply_config(d: dict) -> None:
    pp = d.get("kymographPreprocessing", {})
    dc = pp.get("darkCalibration", KymographPreprocessing().darkCalibration)

    st.session_state.update({
        k: d[k]
        for k in (
            "Dt",
            "Dx",
            "flipIntensity",
            "flowEstimate",
            "tracker",
            "Tlength",
            "thresholdLimit",
            "TmaxNo",
            "exportOptionalFigures",
        )
        if k in d
    })
    st.session_state.update({
        k: pp[k] for k in ("Wx", "Wt", "ws", "removeBackground") if k in pp
    })
    st.session_state.update({
        k: d["Detection"][k]
        for k in ("peakSign", "pfa", "localOptimumRange")
        if k in d.get("Detection", {})
    })
    st.session_state.update({
        k: d["Linking"][k]
        for k in (
            "minTrackLength",
            "cut_off_distance",
            "unmatched_penalty_distance",
            "maxNegativeGab",
            "maxPositiveGab",
            "gab_closing_cut_off_distance",
            "gab_closing_penalty_distance",
        )
        if k in d.get("Linking", {})
    })
    st.session_state["dark_cal_mode"] = "Template" if isinstance(dc, str) else "Scalar"
    if not isinstance(dc, str):
        st.session_state["darkCalibration"] = float(dc)

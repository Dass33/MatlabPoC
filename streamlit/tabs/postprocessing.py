from __future__ import annotations

from dataclasses import dataclass, field
from typing import cast

import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import scipy.io
import streamlit as st

import connectors.algorithms as algorithms
import utils as u
from connectors.algorithms import Collection, MatlabFilterSetting
from core.postprocessing import (
    DIR_OPTIONS,
    FILTER_DEFAULTS,
    MICRO_PROPS,
    SCALAR_PROPS,
    TV_OPTIONS,
    ThresholdConfig,
    build_matlab_setting,
    compute_states,
    default_thresholds,
    filter_collection,
)
from env import job_dirs

_STATES: dict[str, tuple[str, str]] = {
    "auto-kept": ("#0072B2", "circle"),
    "auto-excluded": ("#D55E00", "x"),
    "manual-kept": ("#009E73", "diamond"),
    "manual-excluded": ("#E69F00", "square"),
}

_TRACK_PALETTE: list[str] = [
    "#e6194B",
    "#3cb44b",
    "#ffe119",
    "#4363d8",
    "#f58231",
    "#911eb4",
    "#42d4f4",
    "#f032e6",
    "#bfef45",
    "#469990",
    "#dcbeff",
    "#9A6324",
    "#800000",
    "#aaffc3",
    "#000075",
]


@dataclass
class _PostprocessingState:
    thresholds: dict[str, ThresholdConfig]
    overrides: dict[int, str] = field(default_factory=dict)
    dirty: bool = True
    cal_updates: dict[str, np.ndarray] = field(default_factory=dict)
    calibration: dict[str, object] | None = None


def _get_state(job_id: str) -> _PostprocessingState:
    key = f"pp_{job_id}"
    if key not in st.session_state:
        st.session_state[key] = _PostprocessingState(thresholds=default_thresholds())
    return st.session_state[key]


def page_postprocessing(job_id: str | None) -> None:
    """Post-processing tab — review trajectories, adjust outlier thresholds, run iOC calibration."""
    st.subheader("Post-processing")
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    collection = _load_collection(job_id)
    if collection is None:
        st.warning("collection.mat not found for this job.")
        return

    state = _get_state(job_id)
    _render_postprocessing(job_id, collection, state)


def _render_postprocessing(
    job_id: str, collection: Collection, state: _PostprocessingState
) -> None:
    filter_props = list(FILTER_DEFAULTS)
    effective_collection = cast(Collection, {**collection, **state.cal_updates})

    matlab_setting = build_matlab_setting(state.thresholds)
    n_traj = len(effective_collection["iOC"])
    if matlab_setting["filterProperties"]:
        not_outlier = algorithms.find_outliers(effective_collection, matlab_setting)
    else:
        not_outlier = np.ones(n_traj, dtype=bool)
    states = compute_states(n_traj, not_outlier, state.overrides)
    scalar_props = [p for p in SCALAR_PROPS if p in effective_collection]
    if not scalar_props:
        st.warning("No scalar properties found in collection.")
        return

    default_ax_x = st.session_state.get(f"pp_ax_x_{job_id}", "iOC")
    default_ax_y = st.session_state.get(f"pp_ax_y_{job_id}", "velocity")
    cx, cy, _ = st.columns([1, 1, 3])
    ax_x: str = (
        cx.selectbox(
            "X axis",
            scalar_props,
            index=scalar_props.index(default_ax_x)
            if default_ax_x in scalar_props
            else 0,
            key=f"pp_ax_x_{job_id}",
        )
        or scalar_props[0]
    )
    ax_y: str = (
        cy.selectbox(
            "Y axis",
            scalar_props,
            index=scalar_props.index(default_ax_y)
            if default_ax_y in scalar_props
            else min(1, len(scalar_props) - 1),
            key=f"pp_ax_y_{job_id}",
        )
        or scalar_props[0]
    )

    event = st.plotly_chart(
        _build_scatter(effective_collection, states, ax_x, ax_y),
        use_container_width=True,
        on_select="rerun",
        selection_mode=["lasso", "box"],
        key=f"pp_scatter_{job_id}",
    )

    sel = _parse_selection(event)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Exclude selected", key=f"pp_exclude_{job_id}", disabled=not sel):
        for i in sel:
            state.overrides[i] = "excluded"
        state.dirty = True
        st.rerun()
    if c2.button("Include selected", key=f"pp_include_{job_id}", disabled=not sel):
        for i in sel:
            state.overrides[i] = "kept"
        state.dirty = True
        st.rerun()
    if c3.button(
        "Clear selection overrides", key=f"pp_clear_{job_id}", disabled=not sel
    ):
        for i in sel:
            state.overrides.pop(i, None)
        state.dirty = True
        st.rerun()
    if c4.button(
        "Reset all overrides", key=f"pp_reset_{job_id}", disabled=not state.overrides
    ):
        state.overrides = {}
        state.dirty = True
        st.rerun()

    kept = states.count("auto-kept") + states.count("manual-kept")
    st.caption(
        f"{kept}/{n_traj} kept · {states.count('auto-kept')} auto-kept · {states.count('manual-kept')} manual-kept · {states.count('manual-excluded')} manual-excluded"
    )

    st.divider()
    st.subheader("Outlier thresholds")

    hdr = st.columns([0.4, 1, 1, 2])
    hdr[0].caption("Filter")
    hdr[1].caption("Property")
    hdr[2].caption("Threshold type")
    hdr[3].caption("Direction / value")

    changed = False
    for prop in filter_props:
        cfg = state.thresholds[prop]
        c_en, c0, c1, c2 = st.columns([0.4, 1, 1, 2])
        new_enabled: bool = c_en.checkbox(
            "enabled",
            value=cfg.enabled,
            key=f"pp_en_{job_id}_{prop}",
            label_visibility="collapsed",
        )
        c0.markdown(f"**{prop} (µ)**" if prop in MICRO_PROPS else f"**{prop}**")
        new_tv: str = (
            c1.selectbox(
                "tv",
                TV_OPTIONS,
                index=TV_OPTIONS.index(cfg.tv) if cfg.tv in TV_OPTIONS else 0,
                key=f"pp_tv_{job_id}_{prop}",
                label_visibility="collapsed",
            )
            or cfg.tv
        )
        new_dir: str = (
            c2.selectbox(
                "dir",
                DIR_OPTIONS,
                index=DIR_OPTIONS.index(cfg.direction)
                if cfg.direction in DIR_OPTIONS
                else 0,
                key=f"pp_dir_{job_id}_{prop}",
                label_visibility="collapsed",
            )
            or cfg.direction
        )
        new_val, new_lo, new_hi = cfg.value, cfg.value_lo, cfg.value_hi
        if new_tv == "number":
            unit = " µ" if prop in MICRO_PROPS else ""
            with c2:
                if new_dir == "both":
                    ca, cb = st.columns(2)
                    new_lo = float(
                        ca.number_input(
                            f"lo{unit}",
                            value=cfg.value_lo,
                            key=f"pp_vlo_{job_id}_{prop}",
                            label_visibility="visible",
                        )
                    )
                    new_hi = float(
                        cb.number_input(
                            f"hi{unit}",
                            value=cfg.value_hi,
                            key=f"pp_vhi_{job_id}_{prop}",
                            label_visibility="visible",
                        )
                    )
                else:
                    new_val = float(
                        st.number_input(
                            f"threshold{unit}",
                            value=cfg.value,
                            key=f"pp_val_{job_id}_{prop}",
                            label_visibility="visible",
                        )
                    )
        new_cfg = ThresholdConfig(
            enabled=new_enabled,
            direction=new_dir,
            tv=new_tv,
            value=new_val,
            value_lo=new_lo,
            value_hi=new_hi,
        )
        if new_cfg != cfg:
            state.thresholds[prop] = new_cfg
            changed = True

    if changed:
        state.dirty = True
        st.rerun()

    if state.calibration:
        _render_calibration(state.calibration)

    st.divider()
    with st.expander("Track preview (excluded highlighted)", expanded=True):
        _render_track_preview(effective_collection, states, job_id)

    calibration_on: bool = st.toggle(
        "Run iOC calibration",
        value=True,
        key=f"pp_ioc_cal_{job_id}",
    )

    c_apply, c_hint = st.columns([1, 4])
    if c_apply.button(
        "Accept & Save",
        type="primary" if state.dirty else "secondary",
        key=f"pp_apply_{job_id}",
    ):
        _accept(job_id, collection, states, matlab_setting, calibration_on, state)
    if state.dirty:
        c_hint.caption(
            "Thresholds or selection changed — Accept & Save to recalibrate."
        )


@st.cache_data
def _load_collection(job_id: str) -> Collection | None:
    _, _, out = job_dirs(job_id)
    mat_path = out / "collection" / "collection.mat"
    if not mat_path.exists():
        return None
    m = scipy.io.loadmat(str(mat_path), squeeze_me=True)
    c = m["collection"]
    data = {f: c[f].item() for f in c.dtype.names}
    return cast(Collection, data)


def _build_scatter(
    collection: Collection, states: list[str], x_prop: str, y_prop: str
) -> go.Figure:
    x = np.array(collection.get(x_prop, []), dtype=float)
    y = np.array(collection.get(y_prop, []), dtype=float)
    fig = go.Figure()
    for state, (color, symbol) in _STATES.items():
        idx = [i for i, s in enumerate(states) if s == state]
        if not idx:
            continue
        fig.add_trace(
            go.Scatter(
                x=x[idx],
                y=y[idx],
                mode="markers",
                name=state,
                marker={
                    "size": 9,
                    "color": color,
                    "symbol": symbol,
                    "line": {"width": 1, "color": color},
                },
                customdata=np.array(idx).reshape(-1, 1),
                hovertemplate=f"{x_prop}: %{{x:.4f}}<br>{y_prop}: %{{y:.4f}}<br>idx: %{{customdata[0]}}<extra>{state}</extra>",
            )
        )
    fig.update_layout(
        xaxis_title=x_prop,
        yaxis_title=y_prop,
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        height=450,
        dragmode="lasso",
    )
    return fig


def _parse_selection(event) -> list[int]:
    try:
        pts = event.selection.points
    except AttributeError:
        return []
    result = []
    for pt in pts:
        cd = (
            pt.get("customdata")
            if isinstance(pt, dict)
            else getattr(pt, "customdata", None)
        )
        if cd is not None:
            result.append(int(cd[0]) if isinstance(cd, (list, tuple)) else int(cd))
    return result


def _render_track_preview(
    collection: Collection, states: list[str], job_id: str
) -> None:
    import matplotlib.pyplot as plt

    pos_refined = collection.get("positionRefined")
    if pos_refined is None or len(pos_refined) == 0:
        return

    time_frame = collection.get("timeFrame")
    exp_timestamps = collection.get("ExperimentTimeStamp")
    n_traj = len(pos_refined)

    def get_xy(i: int) -> tuple[np.ndarray, np.ndarray]:
        pos = np.array(pos_refined[i], dtype=float)
        if time_frame is not None:
            try:
                return np.array(time_frame[i], dtype=float), pos
            except (IndexError, TypeError):
                pass
        return np.arange(len(pos), dtype=float), pos

    def ts_str(val) -> str:
        return str(val.flat[0] if isinstance(val, np.ndarray) else val).strip()

    groups: dict[str, list[int]] = {}
    for i in range(n_traj):
        try:
            key = ts_str(exp_timestamps[i]) if exp_timestamps is not None else "all"
        except (IndexError, TypeError):
            key = "all"
        groups.setdefault(key, []).append(i)

    col_sel, _ = st.columns([1, 2])
    selected = col_sel.selectbox(
        "Kymograph", list(groups.keys()), key=f"pp_kymo_sel_{job_id}"
    )

    fig, ax = plt.subplots(figsize=(12, 3))
    fig.patch.set_facecolor("#111111")
    ax.set_facecolor("#111111")
    ax.set_title(selected, color="white", fontsize=8, pad=3)

    for i in groups[selected]:
        frames, pos = get_xy(i)
        if states[i] in ("auto-excluded", "manual-excluded"):
            ax.plot(
                frames,
                pos,
                color=_TRACK_PALETTE[i % len(_TRACK_PALETTE)],
                linewidth=2,
                label=f"#{i}",
            )
        else:
            ax.plot(frames, pos, color="#5599cc", linewidth=1, alpha=0.85)

    ax.invert_yaxis()
    ax.tick_params(colors="white", labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor("#444444")
    handles, labels = ax.get_legend_handles_labels()
    if handles:
        ax.legend(
            handles,
            labels,
            fontsize=7,
            loc="upper right",
            framealpha=0.5,
            labelcolor="white",
            facecolor="#222222",
        )
    ax.set_ylabel("Position (px)", color="white", fontsize=8)
    ax.set_xlabel(
        "Time frame" if time_frame is not None else "Relative frame",
        color="white",
        fontsize=8,
    )

    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _render_calibration(calibration: dict[str, object]) -> None:
    x = calibration["x"]
    fig = sp.make_subplots(rows=1, cols=3, subplot_titles=["A(x)", "Astd(x)", "AN(x)"])
    fig.add_trace(
        go.Scatter(x=x, y=calibration["A"], mode="lines+markers"), row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=x, y=calibration["Astd"], mode="lines+markers"), row=1, col=2
    )
    fig.add_trace(
        go.Scatter(x=x, y=calibration["AN"], mode="lines+markers"), row=1, col=3
    )
    fig.update_layout(
        height=300,
        showlegend=False,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        title_text="iOC Calibration",
    )
    st.plotly_chart(fig, use_container_width=True)


def _accept(
    job_id: str,
    collection: Collection,
    states: list[str],
    matlab_setting: MatlabFilterSetting,
    calibration_on: bool,
    state: _PostprocessingState,
) -> None:
    if calibration_on and (
        collection.get("iOCprofile") is None
        or collection.get("positionRefined") is None
    ):
        st.warning(
            "Collection missing iOCprofile or positionRefined — cannot run calibration."
        )
        return

    _, _, out = job_dirs(job_id)
    n_traj = len(states)
    keep_mask = np.array(
        [state.overrides.get(i) != "excluded" for i in range(n_traj)], dtype=bool
    )
    force_keep = np.array(
        [state.overrides.get(i) == "kept" for i in range(n_traj)], dtype=bool
    )

    with st.spinner("Running postprocessing..."):
        try:
            result = algorithms.run_postprocessing(
                collection, matlab_setting, keep_mask, force_keep, calibration_on
            )
        except (RuntimeError, ValueError) as e:
            st.error(f"Postprocessing failed: {e}")
            return

        cal_updates = {k: result[k] for k in ("iOC", "STDiOC", "N") if k in result}
        calibration = result.get("calibration")
        effective_collection = cast(Collection, {**collection, **cal_updates})

        final_mask = result["notOutlier"]

        collection_postprocessed = {
            "collection": filter_collection(effective_collection, final_mask),
            "calibration": calibration,
            "n_kept": int(final_mask.sum()),
            "n_total": len(final_mask),
        }
        (out / "collection_postprocessed.json").write_text(
            u.to_json(collection_postprocessed)
        )

    state.cal_updates = cal_updates
    state.calibration = calibration
    state.dirty = False

    st.success(
        f"Saved {final_mask.sum()} / {len(final_mask)} trajectories to `collection_postprocessed.json`."
    )
    if calibration:
        _render_calibration(calibration)
    st.info("Head to the **Population Analysis** tab to compute population statistics.")

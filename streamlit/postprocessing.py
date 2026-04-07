"""
Per-property threshold configuration: each property gets its own σ value and direction.
Manual overrides always win over threshold-based classification.
"""

from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
import scipy.io
from algorithms.calibration import run_ioc_calibration
from algorithms.outlier_filtering import find_outliers
from job_manager import job_dirs

import streamlit as st

_STATES = {
    "auto-kept": ("#0072B2", "circle"),
    "auto-excluded": ("#D55E00", "x"),
    "manual-kept": ("#009E73", "diamond"),
    "manual-excluded": ("#E69F00", "square"),
}

_TRACK_PALETTE = [
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

SCALAR_PROPS = ["iOC", "STDiOC", "D", "velocity", "N", "positionStart", "positionEnd"]
_TV_OPTIONS = ["3std", "3std_conditional", "number"]
_DIR_OPTIONS = ["upper", "lower", "both"]


def page_postprocessing(job_id: str | None, config: dict) -> None:
    st.subheader("Post-processing")
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    collection = _load_collection(job_id)
    if collection is None:
        st.warning("collection.mat not found for this job.")
        return

    filt = config.get("outlierFiltering", {})
    st.session_state.setdefault(f"overrides_{job_id}", {})
    st.session_state.setdefault(f"pp_axes_{job_id}", ("iOC", "velocity"))
    if f"pp_thresholds_{job_id}" not in st.session_state:
        props = filt.get("filterProperties", [])
        st.session_state[f"pp_thresholds_{job_id}"] = {
            p: {
                "sigma": 3.0,
                "direction": d,
                "tv": tv,
                "value": 0.0,
                "value_lo": 0.0,
                "value_hi": 0.0,
            }
            for p, d, tv in zip(
                props,
                filt.get("thresholdDirection", []),
                filt.get("thresholdValue", []),
            )
        }

    _render_postprocessing(job_id, collection, filt)


def _render_postprocessing(job_id: str, collection: dict, filt_config: dict) -> None:
    overrides: dict = st.session_state[f"overrides_{job_id}"]
    thresholds: dict = st.session_state[f"pp_thresholds_{job_id}"]
    filter_props = filt_config.get("filterProperties", [])

    not_outlier = find_outliers(collection, filt_config, thresholds)
    n_traj = len(collection["iOC"])
    states = _compute_states(n_traj, not_outlier, overrides)
    scalar_props = [p for p in SCALAR_PROPS if p in collection]

    ax_x, ax_y = st.session_state[f"pp_axes_{job_id}"]
    cx, cy, _ = st.columns([1, 1, 3])
    ax_x = cx.selectbox(
        "X axis",
        scalar_props,
        index=scalar_props.index(ax_x) if ax_x in scalar_props else 0,
        key=f"pp_ax_x_{job_id}",
    )
    ax_y = cy.selectbox(
        "Y axis",
        scalar_props,
        index=scalar_props.index(ax_y) if ax_y in scalar_props else 1,
        key=f"pp_ax_y_{job_id}",
    )
    st.session_state[f"pp_axes_{job_id}"] = (ax_x, ax_y)

    event = st.plotly_chart(
        _build_scatter(collection, states, ax_x, ax_y),
        use_container_width=True,
        on_select="rerun",
        selection_mode=["lasso", "box"],
        key=f"pp_scatter_{job_id}",
    )

    sel = _parse_selection(event)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("Exclude selected", key=f"pp_exclude_{job_id}", disabled=not sel):
        for i in sel:
            overrides[i] = "excluded"
        st.rerun()
    if c2.button("Include selected", key=f"pp_include_{job_id}", disabled=not sel):
        for i in sel:
            overrides[i] = "kept"
        st.rerun()
    if c3.button(
        "Clear selection overrides", key=f"pp_clear_{job_id}", disabled=not sel
    ):
        for i in sel:
            overrides.pop(i, None)
        st.rerun()
    if c4.button(
        "Reset all overrides", key=f"pp_reset_{job_id}", disabled=not overrides
    ):
        st.session_state[f"overrides_{job_id}"] = {}
        st.rerun()

    kept = states.count("auto-kept") + states.count("manual-kept")
    st.caption(
        f"{kept}/{n_traj} kept · {states.count('auto-kept')} auto-kept · {states.count('manual-kept')} manual-kept · {states.count('manual-excluded')} manual-excluded"
    )

    st.divider()
    st.subheader("Outlier thresholds")

    hdr = st.columns([1, 1, 1, 2])
    hdr[0].caption("Property")
    hdr[1].caption("Threshold type")
    hdr[2].caption("Direction")
    hdr[3].caption("σ multiplier")

    changed = False
    for prop in filter_props:
        cfg = thresholds.get(prop, {"sigma": 3.0, "direction": "upper", "tv": "3std"})
        c0, c1, c2, c3 = st.columns([1, 1, 1, 2])
        c0.markdown(f"**{prop}**")
        new_tv = c1.selectbox(
            "tv",
            _TV_OPTIONS,
            index=_TV_OPTIONS.index(cfg["tv"]) if cfg["tv"] in _TV_OPTIONS else 0,
            key=f"pp_tv_{job_id}_{prop}",
            label_visibility="collapsed",
        )
        new_dir = c2.selectbox(
            "dir",
            _DIR_OPTIONS,
            index=_DIR_OPTIONS.index(cfg["direction"])
            if cfg["direction"] in _DIR_OPTIONS
            else 0,
            key=f"pp_dir_{job_id}_{prop}",
            label_visibility="collapsed",
        )
        with c3:
            if new_tv == "number":
                if new_dir == "both":
                    ca, cb = st.columns(2)
                    new_lo = ca.number_input(
                        "lo",
                        value=float(cfg.get("value_lo", 0.0)),
                        key=f"pp_vlo_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_hi = cb.number_input(
                        "hi",
                        value=float(cfg.get("value_hi", 0.0)),
                        key=f"pp_vhi_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_val, new_sigma = cfg.get("value", 0.0), cfg.get("sigma", 3.0)
                else:
                    new_val = st.number_input(
                        "threshold",
                        value=float(cfg.get("value", 0.0)),
                        key=f"pp_val_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_lo, new_hi, new_sigma = (
                        cfg.get("value_lo", 0.0),
                        cfg.get("value_hi", 0.0),
                        cfg.get("sigma", 3.0),
                    )
            else:
                new_sigma = st.slider(
                    "σ",
                    1.0,
                    6.0,
                    float(cfg["sigma"]),
                    0.1,
                    key=f"pp_slider_{job_id}_{prop}",
                    label_visibility="collapsed",
                )
                new_val, new_lo, new_hi = (
                    cfg.get("value", 0.0),
                    cfg.get("value_lo", 0.0),
                    cfg.get("value_hi", 0.0),
                )
        new_cfg = {
            "sigma": new_sigma,
            "direction": new_dir,
            "tv": new_tv,
            "value": new_val,
            "value_lo": new_lo,
            "value_hi": new_hi,
        }
        if new_cfg != cfg:
            thresholds[prop] = new_cfg
            changed = True

    if changed:
        st.rerun()

    st.divider()
    with st.expander("Track preview (excluded highlighted)", expanded=True):
        _render_track_preview(collection, states, job_id)

    calibration_on = st.toggle(
        "Run iOC calibration",
        value=st.session_state.get(f"pp_ioc_cal_{job_id}", True),
        key=f"pp_ioc_cal_{job_id}",
    )
    if st.button("Accept & Save", type="primary", key=f"pp_accept_{job_id}"):
        _accept(job_id, collection, states, calibration_on)


@st.cache_data
def _load_collection(job_id: str) -> dict | None:
    _, _, out = job_dirs(job_id)
    mat_path = out / "collection" / "collection.mat"
    if not mat_path.exists():
        return None

    m = scipy.io.loadmat(str(mat_path), squeeze_me=True)
    c = m["collection"]
    data = {f: c[f].item() for f in c.dtype.names}

    pos = data.get("positionRefined")
    if pos is not None:
        data["positionStart"] = np.array([float(p.min()) for p in pos])
        data["positionEnd"] = np.array([float(p.max()) for p in pos])

    return data


def _compute_states(n: int, not_outlier: np.ndarray, overrides: dict) -> list[str]:
    return [
        ("manual-kept" if overrides[i] == "kept" else "manual-excluded")
        if i in overrides
        else ("auto-kept" if not_outlier[i] else "auto-excluded")
        for i in range(n)
    ]


def _build_scatter(
    collection: dict, states: list[str], x_prop: str, y_prop: str
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


def _render_track_preview(collection: dict, states: list[str], job_id: str) -> None:
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


def _accept(
    job_id: str, collection: dict, states: list[str], calibration_on: bool
) -> None:
    _, _, out = job_dirs(job_id)
    keep_mask = np.array(
        [s in ("auto-kept", "manual-kept") for s in states], dtype=bool
    )
    calibration = None

    with st.spinner("Running iOC calibration..." if calibration_on else "Saving..."):
        if (
            calibration_on
            and collection.get("iOCprofile") is not None
            and collection.get("positionRefined") is not None
        ):
            try:
                calibration, collection = run_ioc_calibration(collection, keep_mask)
            except Exception as e:
                st.warning(f"iOC calibration failed: {e}. Saving without calibration.")

        (out / "collection_postprocessed.json").write_text(
            json.dumps(
                {
                    "collection": _filter_collection(collection, keep_mask),
                    "calibration": calibration,
                    "n_kept": int(keep_mask.sum()),
                    "n_total": len(keep_mask),
                },
                indent=2,
                default=_json_default,
            )
        )

    st.success(
        f"Saved {keep_mask.sum()} / {len(keep_mask)} trajectories to `collection_postprocessed.json`."
    )
    if calibration is not None:
        _render_calibration(calibration)
    st.info("Head to the **Population Analysis** tab to compute population statistics.")


def _filter_collection(collection: dict, keep_mask: np.ndarray) -> dict:
    result = {}
    for k, v in collection.items():
        if isinstance(v, np.ndarray) and len(v) == len(keep_mask):
            result[k] = v[keep_mask].tolist()
        elif isinstance(v, (list, tuple)) and len(v) == len(keep_mask):
            result[k] = [v[i] for i, m in enumerate(keep_mask) if m]
    return result


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    raise TypeError(type(obj))


def _render_calibration(calibration: dict) -> None:
    import plotly.subplots as sp

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

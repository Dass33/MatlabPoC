"""
Per-property threshold configuration: each property gets its own σ value and direction.
Manual overrides always win over threshold-based classification.
Produces A(x), Astd(x), AN(x) curves.
"""

from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
import scipy.io
from job_manager import job_dirs

import streamlit as st

_STATE_COLOR = {
    "auto-kept": "#0072B2",
    "auto-excluded": "#D55E00",
    "manual-kept": "#009E73",
    "manual-excluded": "#E69F00",
}

_STATE_SYMBOL = {
    "auto-kept": "circle",
    "auto-excluded": "x",
    "manual-kept": "diamond",
    "manual-excluded": "square",
}

SCALAR_PROPS = ["iOC", "STDiOC", "D", "velocity", "N", "positionStart", "positionEnd"]

_TV_OPTIONS = ["3std", "3std_conditional", "number"]
_DIR_OPTIONS = ["upper", "lower", "both"]


# ─────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────


def page_postprocessing(job_id: str | None, config: dict) -> None:
    st.subheader("Post-processing")

    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    collection = _load_collection(job_id)
    if collection is None:
        st.warning("collection.mat not found for this job.")
        return

    _init_session_state(job_id, collection, config)
    _render_postprocessing(job_id, collection, config)


# ─────────────────────────────────────────────────────────────────
# Session state helpers
# ─────────────────────────────────────────────────────────────────


def _init_session_state(job_id: str, collection: dict, config: dict) -> None:
    overrides_key = f"overrides_{job_id}"
    thresholds_key = f"pp_thresholds_{job_id}"
    axes_key = f"pp_axes_{job_id}"

    st.session_state.setdefault(overrides_key, {})
    st.session_state.setdefault(axes_key, ("iOC", "velocity"))

    if thresholds_key not in st.session_state:
        filt = config.get("outlierFiltering", {})
        props = filt.get("filterProperties", [])
        directions = filt.get("thresholdDirection", [])
        tvs = filt.get("thresholdValue", [])
        st.session_state[thresholds_key] = {
            p: {
                "sigma": 3.0,
                "direction": d,
                "tv": tv,
                "value": 0.0,
                "value_lo": 0.0,
                "value_hi": 0.0,
            }
            for p, d, tv in zip(props, directions, tvs)
        }


# ─────────────────────────────────────────────────────────────────
# Main fragment
# ─────────────────────────────────────────────────────────────────


@st.fragment
def _render_postprocessing(job_id: str, collection: dict, config: dict) -> None:
    overrides_key = f"overrides_{job_id}"
    thresholds_key = f"pp_thresholds_{job_id}"
    axes_key = f"pp_axes_{job_id}"

    filt_config = config.get("outlierFiltering", {})
    filter_props = filt_config.get("filterProperties", [])

    overrides: dict = st.session_state[overrides_key]
    thresholds: dict = st.session_state[thresholds_key]

    not_outlier = _find_outliers(collection, filt_config, thresholds)

    n_traj = len(collection["iOC"])
    states = _compute_states(n_traj, not_outlier, overrides)

    scalar_props = [p for p in SCALAR_PROPS if p in collection]

    # ── axes selectors ─────────────────────────────────────────
    ax_x, ax_y = st.session_state[axes_key]
    col_x, col_y, _ = st.columns([1, 1, 3])
    with col_x:
        ax_x = st.selectbox(
            "X axis",
            scalar_props,
            index=scalar_props.index(ax_x) if ax_x in scalar_props else 0,
            key=f"pp_ax_x_{job_id}",
        )
    with col_y:
        ax_y = st.selectbox(
            "Y axis",
            scalar_props,
            index=scalar_props.index(ax_y) if ax_y in scalar_props else 1,
            key=f"pp_ax_y_{job_id}",
        )
    st.session_state[axes_key] = (ax_x, ax_y)

    # ── scatter plot ────────────────────────────────────────────
    fig = _build_scatter(collection, states, ax_x, ax_y)
    event = st.plotly_chart(
        fig,
        use_container_width=True,
        on_select="rerun",
        selection_mode=["lasso", "box"],
        key=f"pp_scatter_{job_id}",
    )

    # ── lasso action buttons ────────────────────────────────────
    selected_indices = _parse_selection(event, states)
    col_excl, col_incl, col_clear, col_reset = st.columns(4)
    with col_excl:
        if st.button(
            "Exclude selected",
            key=f"pp_exclude_{job_id}",
            disabled=not selected_indices,
        ):
            for i in selected_indices:
                overrides[i] = "excluded"
            st.rerun(scope="fragment")
    with col_incl:
        if st.button(
            "Include selected",
            key=f"pp_include_{job_id}",
            disabled=not selected_indices,
        ):
            for i in selected_indices:
                overrides[i] = "kept"
            st.rerun(scope="fragment")
    with col_clear:
        if st.button(
            "Clear selection overrides",
            key=f"pp_clear_{job_id}",
            disabled=not selected_indices,
        ):
            for i in selected_indices:
                overrides.pop(i, None)
            st.rerun(scope="fragment")
    with col_reset:
        if st.button(
            "Reset all overrides", key=f"pp_reset_{job_id}", disabled=not overrides
        ):
            st.session_state[overrides_key] = {}
            st.rerun(scope="fragment")

    kept = sum(1 for s in states if s in ("auto-kept", "manual-kept"))
    st.caption(
        f"{kept} / {n_traj} kept  ·  "
        f"{sum(1 for s in states if s == 'auto-kept')} auto-kept  ·  "
        f"{sum(1 for s in states if s == 'manual-kept')} manual-kept  ·  "
        f"{sum(1 for s in states if s == 'manual-excluded')} manual-excluded"
    )

    st.divider()

    # ── threshold controls ──────────────────────────────────────
    st.subheader("Outlier thresholds")
    hdr = st.columns([1, 1, 1, 2])
    hdr[0].caption("Property")
    hdr[1].caption("Threshold type")
    hdr[2].caption("Direction")
    hdr[3].caption("σ multiplier")

    changed = False
    for prop in filter_props:
        cfg = thresholds.get(prop, {"sigma": 3.0, "direction": "upper", "tv": "3std"})
        cols = st.columns([1, 1, 1, 2])
        cols[0].markdown(f"**{prop}**")
        with cols[1]:
            new_tv = st.selectbox(
                "tv",
                _TV_OPTIONS,
                index=_TV_OPTIONS.index(cfg["tv"]) if cfg["tv"] in _TV_OPTIONS else 0,
                key=f"pp_tv_{job_id}_{prop}",
                label_visibility="collapsed",
            )
        with cols[2]:
            new_dir = st.selectbox(
                "dir",
                _DIR_OPTIONS,
                index=_DIR_OPTIONS.index(cfg["direction"])
                if cfg["direction"] in _DIR_OPTIONS
                else 0,
                key=f"pp_dir_{job_id}_{prop}",
                label_visibility="collapsed",
            )
        with cols[3]:
            if new_tv == "number":
                if new_dir == "both":
                    c_lo, c_hi = st.columns(2)
                    new_value_lo = c_lo.number_input(
                        "lo",
                        value=float(cfg.get("value_lo", 0.0)),
                        key=f"pp_vlo_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_value_hi = c_hi.number_input(
                        "hi",
                        value=float(cfg.get("value_hi", 0.0)),
                        key=f"pp_vhi_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_value = cfg.get("value", 0.0)
                else:
                    new_value = st.number_input(
                        "threshold",
                        value=float(cfg.get("value", 0.0)),
                        key=f"pp_val_{job_id}_{prop}",
                        label_visibility="collapsed",
                    )
                    new_value_lo = cfg.get("value_lo", 0.0)
                    new_value_hi = cfg.get("value_hi", 0.0)
                new_sigma = cfg.get("sigma", 3.0)
            else:
                new_sigma = st.slider(
                    "σ",
                    min_value=1.0,
                    max_value=6.0,
                    value=float(cfg["sigma"]),
                    step=0.1,
                    key=f"pp_slider_{job_id}_{prop}",
                    label_visibility="collapsed",
                )
                new_value = cfg.get("value", 0.0)
                new_value_lo = cfg.get("value_lo", 0.0)
                new_value_hi = cfg.get("value_hi", 0.0)
        new_cfg = {
            "sigma": new_sigma,
            "direction": new_dir,
            "tv": new_tv,
            "value": new_value,
            "value_lo": new_value_lo,
            "value_hi": new_value_hi,
        }
        if new_cfg != cfg:
            thresholds[prop] = new_cfg
            changed = True

    if changed:
        st.rerun(scope="fragment")

    st.divider()

    # ── Accept & Save ───────────────────────────────────────────
    calibration_on = st.toggle(
        "Run iOC calibration",
        value=st.session_state.get(f"pp_ioc_cal_{job_id}", True),
        key=f"pp_ioc_cal_{job_id}",
    )
    accept = st.button("Accept & Save", type="primary", key=f"pp_accept_{job_id}")

    if accept:
        _accept(job_id, collection, states, calibration_on)


# ─────────────────────────────────────────────────────────────────
# Core logic
# ─────────────────────────────────────────────────────────────────


def _load_collection(job_id: str) -> dict | None:
    _, _, out = job_dirs(job_id)
    mat_path = out / "collection" / "collection.mat"
    if not mat_path.exists():
        return None

    m = scipy.io.loadmat(str(mat_path), squeeze_me=True)
    c = m["collection"]
    data: dict = {}
    for f in c.dtype.names:
        v = c[f].item()
        data[f] = v

    pos = data.get("positionRefined")
    if pos is not None:
        data["positionStart"] = np.array([float(p.min()) for p in pos])
        data["positionEnd"] = np.array([float(p.max()) for p in pos])

    return data


def _find_outliers(collection: dict, filt_config: dict, thresholds: dict) -> np.ndarray:
    """Port of findTrajectoryOutliers.m. Returns bool array: True = not outlier."""
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

    max_iter = 100
    for _ in range(max_iter):
        if np.array_equal(not_outlier, not_outlier0):
            break
        not_outlier0 = not_outlier.copy()

        per_prop = []
        for prop in filter_props:
            if prop not in collection:
                per_prop.append(np.ones(n, dtype=bool))
                continue

            cfg = thresholds.get(
                prop, {"sigma": 3.0, "direction": "upper", "tv": "3std"}
            )
            direction = cfg.get("direction", "upper")
            tv = cfg.get("tv", "3std")
            sigma = float(cfg.get("sigma", 3.0))

            y = np.array(collection[prop], dtype=float)

            if tv == "3std":
                y_in = y[not_outlier0]
                mean_v = np.nanmean(y_in)
                std_v = np.nanstd(y_in, ddof=1) if len(y_in) > 1 else 1.0
                lo = mean_v - sigma * std_v
                hi = mean_v + sigma * std_v

            elif tv == "3std_conditional":
                x_ref = ref
                y_in = y[not_outlier0]
                x_in = x_ref[not_outlier0]
                A = np.column_stack([x_in, np.ones(len(x_in))])
                p, *_ = np.linalg.lstsq(A, y_in, rcond=None)
                fitted = p[0] * x_ref + p[1]
                ratio = y_in / (p[0] * x_in + p[1])
                mean_r = np.nanmean(ratio)
                std_r = np.nanstd(ratio, ddof=1) if len(ratio) > 1 else 1.0
                lo = (mean_r - sigma * std_r) * fitted
                hi = (mean_r + sigma * std_r) * fitted

            else:  # "number"
                if direction == "both":
                    lo = float(cfg.get("value_lo", 0.0))
                    hi = float(cfg.get("value_hi", 0.0))
                elif direction == "lower":
                    lo = float(cfg.get("value", 0.0))
                    hi = np.inf
                else:  # upper
                    lo = -np.inf
                    hi = float(cfg.get("value", 0.0))

            if direction == "upper":
                lo = -np.inf if np.isscalar(lo) else np.full(n, -np.inf)
            elif direction == "lower":
                hi = np.inf if np.isscalar(hi) else np.full(n, np.inf)

            per_prop.append((y > lo) & (y < hi))

        not_outlier = np.asarray(np.stack(per_prop, axis=0).all(axis=0))

    return not_outlier


def _compute_states(n: int, not_outlier: np.ndarray, overrides: dict) -> list[str]:
    states = []
    for i in range(n):
        if i in overrides:
            states.append(
                "manual-kept" if overrides[i] == "kept" else "manual-excluded"
            )
        else:
            states.append("auto-kept" if not_outlier[i] else "auto-excluded")
    return states


def _build_scatter(
    collection: dict, states: list[str], x_prop: str, y_prop: str
) -> go.Figure:
    x = np.array(collection.get(x_prop, []), dtype=float)
    y = np.array(collection.get(y_prop, []), dtype=float)

    fig = go.Figure()
    for state, symbol in _STATE_SYMBOL.items():
        color = _STATE_COLOR[state]
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
                hovertemplate=(
                    f"{x_prop}: %{{x:.4f}}<br>{y_prop}: %{{y:.4f}}<br>"
                    f"idx: %{{customdata[0]}}<extra>{state}</extra>"
                ),
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


def _parse_selection(event, states: list[str]) -> list[int]:
    if event is None:
        return []
    try:
        points = event.selection.points
    except AttributeError:
        return []
    global_indices = []
    for pt in points:
        cd = (
            pt.get("customdata")
            if isinstance(pt, dict)
            else getattr(pt, "customdata", None)
        )
        if cd is None:
            continue
        # customdata is [[idx]] shape → comes through as [idx] per point
        if isinstance(cd, (list, tuple)):
            global_indices.append(int(cd[0]))
        else:
            global_indices.append(int(cd))
    return global_indices


# ─────────────────────────────────────────────────────────────────
# Accept: calibrate + save
# ─────────────────────────────────────────────────────────────────


def _accept(
    job_id: str, collection: dict, states: list[str], calibration_on: bool
) -> None:
    _, _, out = job_dirs(job_id)
    keep_mask = np.array(
        [s in ("auto-kept", "manual-kept") for s in states], dtype=bool
    )

    calibration = None

    with st.spinner("Running iOC calibration..." if calibration_on else "Saving..."):
        if calibration_on:
            ioc_profiles = collection.get("iOCprofile")
            pos_refined = collection.get("positionRefined")
            if ioc_profiles is not None and pos_refined is not None:
                try:
                    calibration, collection = _run_ioc_calibration(
                        collection, keep_mask
                    )
                except Exception as e:
                    st.warning(
                        f"iOC calibration failed: {e}. Saving without calibration."
                    )

        filtered = _filter_collection(collection, keep_mask)
        output = {
            "collection": filtered,
            "calibration": calibration,
            "n_kept": int(keep_mask.sum()),
            "n_total": len(keep_mask),
        }

        out_path = out / "collection_postprocessed.json"
        out_path.write_text(json.dumps(output, indent=2, default=_json_default))

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
            kept = v[keep_mask]
            result[k] = kept.tolist()
        elif isinstance(v, (list, tuple)) and len(v) == len(keep_mask):
            result[k] = [v[i] for i, m in enumerate(keep_mask) if m]
    return result


def _json_default(obj):
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    raise TypeError(f"Not serializable: {type(obj)}")


# ─────────────────────────────────────────────────────────────────
# iOC calibration (port of iOCcalibration.m)
# ─────────────────────────────────────────────────────────────────


def _run_ioc_calibration(collection: dict, keep_mask: np.ndarray) -> tuple[dict, dict]:
    """
    Port of iOCcalibration.m.
    Estimates position-dependent amplitude A(x) from kept trajectories,
    then recalibrates iOC/STDiOC/N for all trajectories.
    Returns (calibration_dict, updated_collection).
    """
    ioc_profiles = collection["iOCprofile"]
    pos_refined = collection["positionRefined"]

    kept_idx = np.where(keep_mask)[0]
    ioc_kept = [ioc_profiles[i] for i in kept_idx]
    pos_kept = [pos_refined[i] for i in kept_idx]

    calibration = _ioc_calibration_core(ioc_kept, pos_kept)

    cal_x = np.array(calibration["x"])
    cal_A = np.array(calibration["A"])

    updated = dict(collection)
    n_traj = len(collection["iOC"])
    new_ioc = np.array(collection["iOC"], dtype=float)
    new_std = np.array(collection["STDiOC"], dtype=float)
    new_N = np.array(collection["N"], dtype=float)

    for i in range(n_traj):
        pos_i = np.array(pos_refined[i], dtype=float)
        ioc_i = np.array(ioc_profiles[i], dtype=float)
        A_int = np.interp(pos_i, cal_x, cal_A)
        Y = ioc_i / A_int
        std_v, mean_v, selected = _std_modified(Y, fun_mean=1, fun_stabil=1)
        new_std[i] = std_v
        new_ioc[i] = mean_v
        new_N[i] = float(selected.sum())

    updated["iOC"] = new_ioc
    updated["STDiOC"] = new_std
    updated["N"] = new_N

    return calibration, updated


def _ioc_calibration_core(
    ioc_profiles: list, positions: list, dx: float = 1.0, threshold: float = 1e-3
) -> dict:
    n_traj = len(ioc_profiles)

    pos_starts = [float(p.min()) for p in positions]
    pos_ends = [float(p.max()) for p in positions]
    pos_start = max(pos_starts)
    pos_end = min(pos_ends)

    # flatten all positions and iOC values; keep per-trajectory index ranges
    ind_i = []
    a = 0
    for p in positions:
        ind_i.append(slice(a, a + len(p)))
        a += len(p)

    all_pos = np.concatenate([np.array(p, dtype=float) for p in positions])
    all_ioc = np.concatenate([np.array(s, dtype=float) for s in ioc_profiles])

    x = np.arange(pos_start + dx / 2, pos_end - dx / 2 + 1, dx)
    if len(x) == 0:
        x = np.array([(pos_start + pos_end) / 2])

    ind_x = [
        np.where((all_pos >= xi - dx / 2) & (all_pos <= xi + dx / 2))[0] for xi in x
    ]

    not_outlier_frame = (all_pos >= x[0]) & (all_pos <= x[-1])
    not_outlier_frame0 = ~not_outlier_frame.copy()

    Aint = np.ones_like(all_ioc)
    ioc_norm = np.ones_like(all_ioc)
    A = np.zeros(len(x))
    A0 = np.full(len(x), np.inf)
    Astd = np.zeros(len(x))
    AN = np.zeros(len(x))

    max_iter = 100
    for _ in range(max_iter):
        if np.array_equal(not_outlier_frame, not_outlier_frame0) and np.all(
            np.abs(A - A0) <= threshold
        ):
            break
        not_outlier_frame0 = not_outlier_frame.copy()
        A0 = A.copy()

        Y = all_ioc / Aint
        for i in range(n_traj):
            sl = ind_i[i]
            valid = np.where(not_outlier_frame[sl])[0]
            if len(valid) == 0:
                continue
            mean_ioc = np.nanmean(Y[sl][valid])
            if mean_ioc == 0 or np.isnan(mean_ioc):
                continue
            ioc_norm[sl] = all_ioc[sl] / mean_ioc

        Y2 = ioc_norm / Aint
        _, _, selected = _std_modified(Y2[not_outlier_frame], fun_mean=1, fun_stabil=1)
        nof_idx = np.where(not_outlier_frame)[0]
        not_outlier_frame[nof_idx] = selected

        A_new = np.zeros(len(x))
        Astd = np.zeros(len(x))
        AN = np.zeros(len(x))
        for i, ix in enumerate(ind_x):
            valid = ix[not_outlier_frame[ix]]
            if len(valid) == 0:
                A_new[i] = np.nan
                Astd[i] = np.nan
                AN[i] = 0
            else:
                A_new[i] = np.nanmean(ioc_norm[valid])
                Astd[i] = np.nanstd(ioc_norm[valid], ddof=1) if len(valid) > 1 else 0.0
                AN[i] = len(valid)

        A_mean = np.nanmean(A_new)
        if A_mean and not np.isnan(A_mean):
            A = A_new / A_mean
        else:
            A = A_new

        Aint = np.interp(all_pos, x, A)

    return {"x": x.tolist(), "A": A.tolist(), "Astd": Astd.tolist(), "AN": AN.tolist()}


def _std_modified(
    x: np.ndarray, fun_mean: int = 1, fun_stabil: int = 1
) -> tuple[float, float, np.ndarray]:
    """Port of std_modified.m. Returns (STD, MEAN, selected bool array)."""
    x = np.array(x, dtype=float)
    selected = ~(np.isnan(x) | np.isinf(x))

    if fun_mean == 0:
        std_v = np.sqrt(np.sum(x[selected] ** 2) / max(selected.sum() - 1, 1))
        mean_v = 0.0
        if fun_stabil == 1 and selected.sum() > 1:
            sel0 = selected.copy()
            selected = np.abs(x) < 3 * std_v
            while selected.sum() < sel0.sum():
                std_v = np.sqrt(np.sum(x[selected] ** 2) / max(selected.sum() - 1, 1))
                sel0 = selected.copy()
                selected = np.abs(x) < 3 * std_v
    else:
        mean_v = np.nanmean(x[selected])
        std_v = np.sqrt(
            np.sum((x[selected] - mean_v) ** 2) / max(selected.sum() - 1, 1)
        )
        if fun_stabil == 1 and selected.sum() > 1:
            sel0 = selected.copy()
            selected = np.abs(x - mean_v) < 3 * std_v
            while selected.sum() < sel0.sum():
                mean_v = np.nanmean(x[selected])
                std_v = np.sqrt(
                    np.sum((x[selected] - mean_v) ** 2) / max(selected.sum() - 1, 1)
                )
                sel0 = selected.copy()
                selected = np.abs(x - mean_v) < 3 * std_v

    return float(std_v), float(mean_v), selected


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

"""
Two methods: robustMean and gaussFit, selectable by user.
noPopulation parameter: number of expected clusters/sub-populations.
Runs entirely in Python — scipy for Gaussian fitting, numpy for robust statistics.
User can go back to thersholding (postprocessing) to redo outlier filtering at any point.
"""

from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
from job_manager import job_dirs

import streamlit as st

AVAILABLE_PROPS = ["iOC", "D", "velocity"]


def page_population_analysis(job_id: str | None, config: dict) -> None:
    st.subheader("Population Analysis")

    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    _, _, out = job_dirs(job_id)
    pp_path = out / "collection_postprocessed.json"

    if not pp_path.exists():
        st.warning(
            "No postprocessed collection found. "
            "Run postprocessing first and click **Accept & Save**."
        )
        return

    data = json.loads(pp_path.read_text())
    collection = data.get("collection", {})
    n_kept = data.get("n_kept", "?")
    n_total = data.get("n_total", "?")
    st.caption(f"Using {n_kept} / {n_total} trajectories from postprocessing.")

    pop_config = config.get("populationAnalysis", {})
    default_method = pop_config.get("Title", "robustMean")
    default_props = pop_config.get("properties", AVAILABLE_PROPS)

    available = [p for p in AVAILABLE_PROPS if p in collection]
    if not available:
        st.error(
            "No recognised properties (iOC, D, velocity) found in postprocessed collection."
        )
        return

    col_method, col_props = st.columns([1, 2])
    with col_method:
        method = st.selectbox(
            "Method",
            ["robustMean", "gaussFit"],
            index=0 if default_method == "robustMean" else 1,
            key=f"pop_method_{job_id}",
        )
    with col_props:
        selected_props = st.multiselect(
            "Properties",
            available,
            default=[p for p in default_props if p in available],
            key=f"pop_props_{job_id}",
        )

    if not selected_props:
        st.info("Select at least one property.")
        return

    if st.button("Run Population Analysis", type="primary", key=f"pop_run_{job_id}"):
        with st.spinner("Computing..."):
            try:
                if method == "robustMean":
                    result = _robust_mean(collection, selected_props)
                else:
                    result = _gauss_fit(collection, selected_props)
            except Exception as e:
                st.error(f"Population analysis failed: {e}")
                return

        _save_population(out, result, method, selected_props, n_kept)
        st.session_state[f"pop_result_{job_id}"] = result
        st.session_state[f"pop_method_used_{job_id}"] = method
        st.session_state[f"pop_props_used_{job_id}"] = selected_props

    result = st.session_state.get(f"pop_result_{job_id}")
    if result is None:
        return

    method_used = st.session_state.get(f"pop_method_used_{job_id}", method)
    props_used = st.session_state.get(f"pop_props_used_{job_id}", selected_props)

    _render_results_table(result, props_used)
    _render_histograms(collection, result, props_used, job_id, method_used)

    st.info(
        "Not happy with the result? Go back to **Postprocessing** to adjust outlier thresholds "
        "and accept again, then re-run here."
    )


# ─────────────────────────────────────────────────────────────────
# robustMean (port of analyzePopulation_robustMean.m + std_modified_ND.m)
# ─────────────────────────────────────────────────────────────────


def _robust_mean(collection: dict, props: list[str]) -> dict:
    arrays = [np.array(collection[p], dtype=float) for p in props]
    Y = np.stack(arrays, axis=0)  # (n_props, n_traj)

    weights = np.array(collection.get("N", []), dtype=float)
    if len(weights) != Y.shape[1]:
        weights = None

    selected = ~np.any(np.isnan(Y), axis=0)
    selected0 = ~selected.copy()
    mean_v = np.full(len(props), np.nan)
    std_v = np.full(len(props), np.nan)

    max_iter = 100
    for _ in range(max_iter):
        if np.array_equal(selected, selected0):
            break
        selected0 = selected.copy()

        Y_sel = Y[:, selected]
        if weights is not None:
            w_sel = weights[selected]
            w_sum = w_sel.sum()
            mean_v = (Y_sel * w_sel).sum(axis=1) / w_sum
            std_v = np.sqrt(
                (w_sel * (Y_sel - mean_v[:, None]) ** 2).sum(axis=1) / w_sum
            )
        else:
            mean_v = Y_sel.mean(axis=1)
            std_v = Y_sel.std(axis=1, ddof=0)

        std_safe = np.where(std_v == 0, 1.0, std_v)
        R = np.sum(
            ((Y[:, selected] - mean_v[:, None]) / (std_safe[:, None] * 3)) ** 2, axis=0
        )
        selected[selected] = R < 1

    result = {}
    for i, prop in enumerate(props):
        fwhm = 2 * np.sqrt(2 * np.log(2)) * std_v[i]
        result[prop] = {
            "MEAN": float(mean_v[i]),
            "STD": float(std_v[i]),
            "FWHM": float(fwhm),
            "RESOLUTION": float(abs(mean_v[i]) / fwhm) if fwhm != 0 else float("nan"),
        }
    return result


# ─────────────────────────────────────────────────────────────────
# gaussFit (port of analyzePopulation_gaussFit.m)
# ─────────────────────────────────────────────────────────────────


def _gauss_fit(collection: dict, props: list[str]) -> dict:
    from scipy.optimize import curve_fit

    N_field = collection.get("N")

    result = {}
    for prop in props:
        Y = np.array(collection[prop], dtype=float)
        Y = Y[~np.isnan(Y)]

        mean_est = float(np.median(Y))
        std_est = float(np.median(np.abs(Y - mean_est)) / 0.6745)
        n_est = int(np.sum((Y > mean_est - 3 * std_est) & (Y < mean_est + 3 * std_est)))

        # Expand by track length if N available
        if N_field is not None and len(N_field) == len(collection[prop]):
            N_arr = np.array(N_field, dtype=int)
            Y_prop = np.array(collection[prop], dtype=float)
            Y_expanded = np.repeat(Y_prop, N_arr)
            Y_expanded = Y_expanded[~np.isnan(Y_expanded)]
        else:
            Y_expanded = Y

        dx = 3.5 * std_est / max(n_est ** (1 / 3), 1)
        edges = np.arange(Y_expanded.min() - dx / 2, Y_expanded.max() + dx / 2 + dx, dx)
        counts, _ = np.histogram(Y_expanded, bins=edges)
        centers = (edges[:-1] + edges[1:]) / 2

        def gaussian(x, amp, mu, sig):
            return amp * np.exp(-((x - mu) ** 2) / (2 * sig**2))

        try:
            amp0 = float(np.interp(mean_est, centers, counts.astype(float)))
            popt, _ = curve_fit(
                gaussian,
                centers,
                counts.astype(float),
                p0=[amp0, mean_est, std_est],
                maxfev=10000,
            )
            fit_mean = float(popt[1])
            fit_std = float(abs(popt[2]))
        except Exception:
            fit_mean = mean_est
            fit_std = std_est

        fwhm = 2 * np.sqrt(2 * np.log(2)) * fit_std
        result[prop] = {
            "MEAN": fit_mean,
            "STD": fit_std,
            "FWHM": fwhm,
            "RESOLUTION": float(abs(fit_mean) / fwhm) if fwhm != 0 else float("nan"),
            "_hist_centers": centers.tolist(),
            "_hist_counts": counts.tolist(),
        }
    return result


# ─────────────────────────────────────────────────────────────────
# Rendering
# ─────────────────────────────────────────────────────────────────


def _render_results_table(result: dict, props: list[str]) -> None:
    import pandas as pd

    rows = []
    for prop in props:
        r = result.get(prop, {})
        rows.append({
            "Property": prop,
            "MEAN": r.get("MEAN", float("nan")),
            "STD": r.get("STD", float("nan")),
            "FWHM": r.get("FWHM", float("nan")),
            "RESOLUTION": r.get("RESOLUTION", float("nan")),
        })
    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, use_container_width=True)


def _render_histograms(
    collection: dict, result: dict, props: list[str], job_id: str, method: str
) -> None:
    n_props = len(props)
    if n_props == 0:
        return

    fig = sp.make_subplots(rows=1, cols=n_props, subplot_titles=props)

    for col_idx, prop in enumerate(props, start=1):
        r = result.get(prop, {})
        Y = np.array(collection.get(prop, []), dtype=float)
        Y = Y[~np.isnan(Y)]

        if len(Y) == 0:
            continue

        fig.add_trace(
            go.Histogram(
                x=Y,
                nbinsx=20,
                marker_color="#4C72B0",
                opacity=0.7,
                name=prop,
                showlegend=False,
            ),
            row=1,
            col=col_idx,
        )

        if method == "gaussFit" and "_hist_centers" in r:
            centers = np.array(r["_hist_centers"])
            fit_mean = r["MEAN"]
            fit_std = r["STD"]
            counts = np.array(r["_hist_counts"])
            amp = float(counts.max()) if len(counts) > 0 else 1.0
            x_fine = np.linspace(centers[0], centers[-1], 200)
            y_fine = amp * np.exp(-((x_fine - fit_mean) ** 2) / (2 * fit_std**2))
            fig.add_trace(
                go.Scatter(
                    x=x_fine,
                    y=y_fine,
                    mode="lines",
                    line={"color": "#D9534F", "width": 2},
                    name=f"{prop} fit",
                    showlegend=False,
                ),
                row=1,
                col=col_idx,
            )
        elif method == "robustMean":
            fit_mean = r.get("MEAN", 0)
            fig.add_shape(
                type="line",
                x0=fit_mean,
                x1=fit_mean,
                y0=0,
                y1=1,
                yref="paper",
                line={"color": "#D9534F", "width": 2, "dash": "dash"},
                row=1,
                col=col_idx,
            )

    fig.update_layout(
        height=300,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# Save
# ─────────────────────────────────────────────────────────────────


def _save_population(out, result: dict, method: str, props: list[str], n_kept) -> None:
    clean_result = {}
    for prop, r in result.items():
        clean_result[prop] = {k: v for k, v in r.items() if not k.startswith("_")}

    payload = {
        "method": method,
        "properties": props,
        "n_trajectories": n_kept,
        "results": clean_result,
    }

    def _default(obj):
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(type(obj))

    (out / "population.json").write_text(
        json.dumps(payload, indent=2, default=_default)
    )

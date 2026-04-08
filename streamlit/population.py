"""
Two methods: robustMean and gaussFit, selectable by user.
Runs entirely in Python — scipy for Gaussian fitting, numpy for robust statistics.
"""

from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
import plotly.subplots as sp
import matlab_bridge
from job_manager import job_dirs

import streamlit as st

AVAILABLE_PROPS = [
    "iOC",
    "D",
    "STDiOC",
    "velocity",
    "N",
    "positionStart",
    "positionEnd",
]


def page_population_analysis(job_id: str | None, config: dict) -> None:
    st.subheader("Population Analysis")
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    _, _, out = job_dirs(job_id)
    pp_path = out / "collection_postprocessed.json"
    if not pp_path.exists():
        st.warning(
            "No postprocessed collection found. Run postprocessing first and click **Accept & Save**."
        )
        return

    data = json.loads(pp_path.read_text())
    collection = data.get("collection", {})
    st.caption(
        f"Using {data.get('n_kept', '?')} / {data.get('n_total', '?')} trajectories from postprocessing."
    )

    available = [p for p in AVAILABLE_PROPS if p in collection]
    if not available:
        st.error(
            "No recognised properties (iOC, D, velocity) found in postprocessed collection."
        )
        return

    pop_config = config.get("populationAnalysis", {})
    default_method = pop_config.get("Title", "robustMean")
    default_props = pop_config.get("properties", AVAILABLE_PROPS)

    cm, cp = st.columns([1, 2])
    method = cm.selectbox(
        "Method",
        ["robustMean", "gaussFit"],
        index=0 if default_method == "robustMean" else 1,
        key=f"pop_method_{job_id}",
    )
    selected_props = cp.multiselect(
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
                result = matlab_bridge.run_population_analysis(
                    collection,
                    {"Title": method, "properties": selected_props},
                )
            except Exception as e:
                st.error(f"Population analysis failed: {e}")
                return
        _save_population(out, result, method, selected_props, data.get("n_kept"))
        st.session_state[f"pop_result_{job_id}"] = result
        st.session_state[f"pop_method_used_{job_id}"] = method
        st.session_state[f"pop_props_used_{job_id}"] = selected_props

    result = st.session_state.get(f"pop_result_{job_id}")
    if result is None:
        return

    method_used = st.session_state.get(f"pop_method_used_{job_id}", method)
    props_used = st.session_state.get(f"pop_props_used_{job_id}", selected_props)

    import pandas as pd

    keys = ["MEAN", "STD", "FWHM", "RESOLUTION"]
    st.dataframe(
        pd.DataFrame([
            {"Property": p, **{k: result.get(p, {}).get(k, float("nan")) for k in keys}}
            for p in props_used
        ]),
        hide_index=True,
        use_container_width=True,
    )
    _render_histograms(collection, result, props_used, method_used)


# ─── robustMean (port of analyzePopulation_robustMean.m + std_modified_ND.m) ───


def _render_histograms(
    collection: dict, result: dict, props: list[str], method: str
) -> None:
    if not props:
        return
    fig = sp.make_subplots(rows=1, cols=len(props), subplot_titles=props)
    for col, prop in enumerate(props, 1):
        r = result.get(prop, {})
        Y = np.array(collection.get(prop, []), dtype=float)
        Y = Y[~np.isnan(Y)]
        if not len(Y):
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
            col=col,
        )
        if method == "gaussFit" and "_hist_centers" in r:
            centers = np.array(r["_hist_centers"])
            x_fine = np.linspace(centers[0], centers[-1], 200)
            y_fine = float(np.array(r["_hist_counts"]).max()) * np.exp(
                -((x_fine - r["MEAN"]) ** 2) / (2 * r["STD"] ** 2)
            )
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
                col=col,
            )
        elif method == "robustMean":
            fig.add_shape(
                type="line",
                x0=r.get("MEAN", 0),
                x1=r.get("MEAN", 0),
                y0=0,
                y1=1,
                yref="paper",
                line={"color": "#D9534F", "width": 2, "dash": "dash"},
                row=1,
                col=col,
            )
    fig.update_layout(
        height=300, margin={"l": 40, "r": 20, "t": 40, "b": 40}, bargap=0.05
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── Save ───


def _save_population(out, result: dict, method: str, props: list[str], n_kept) -> None:
    def _default(obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(type(obj))

    (out / "population.json").write_text(
        json.dumps(
            {
                "method": method,
                "properties": props,
                "n_trajectories": n_kept,
                "results": {
                    p: {k: v for k, v in r.items() if not k.startswith("_")}
                    for p, r in result.items()
                },
            },
            indent=2,
            default=_default,
        )
    )

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import streamlit as st

import utils as u
from connectors import algorithms
from connectors.storage import list_completed_jobs
from core.postprocessing import AVAILABLE_PROPS, MICRO_PROPS
from env import job_dirs

_SCALED_KEYS = {"MEAN", "STD", "FWHM"}
_COMPARE_COLORS = ["#4C72B0", "#D9534F", "#55A868"]


@dataclass
class _PopResult:
    result: dict[str, Any]
    method: str
    props: list[str]


def _display_val(prop: str, key: str, val: float) -> float:
    if prop in MICRO_PROPS and key in _SCALED_KEYS:
        return val * 1e6
    return val


@st.fragment
def page_population_analysis(job_id: str | None) -> None:
    """Population Analysis tab - compute population statistics on a postprocessed collection."""
    st.subheader("Population Analysis")
    _render_single_job_section(job_id)
    _render_compare_section()


def _render_single_job_section(job_id: str | None) -> None:
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

    default_method = "robustMean"
    default_props = AVAILABLE_PROPS

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

    if len(selected_props) < 2:
        st.warning("Select at least 2 properties.")
        return

    if st.button("Run Population Analysis", type="primary", key=f"pop_run_{job_id}"):
        with st.spinner("Computing..."):
            try:
                result = algorithms.run_population_analysis(
                    collection,
                    {"Title": method, "properties": selected_props},
                )
            except Exception as e:  # includes opaque MatlabRuntimeError
                st.error(f"Population analysis failed: {e}")
                return
        _save_population(out, result, method, selected_props, data.get("n_kept"))
        st.session_state[f"pop_{job_id}"] = _PopResult(
            result=result, method=method, props=selected_props
        )

    pop: _PopResult | None = st.session_state.get(f"pop_{job_id}")
    if pop is None:
        return

    result = pop.result
    method_used = pop.method
    props_used = pop.props

    keys = ["MEAN", "STD", "FWHM", "RESOLUTION"]

    st.dataframe(
        pd.DataFrame([
            {
                "Property": f"{p} (µ)" if p in MICRO_PROPS else p,
                **{
                    k: _display_val(p, k, result.get(p, {}).get(k, float("nan")))
                    for k in keys
                },
            }
            for p in props_used
        ]),
        hide_index=True,
        use_container_width=True,
    )
    _render_histograms(collection, result, props_used, method_used)


def _render_histograms(
    collection: dict, result: dict, props: list[str], method: str
) -> None:
    if not props:
        return
    titles = [f"{p} (µ)" if p in MICRO_PROPS else p for p in props]
    fig = sp.make_subplots(rows=1, cols=len(props), subplot_titles=titles)
    for col, prop in enumerate(props, 1):
        r = result.get(prop, {})
        scale = 1e6 if prop in MICRO_PROPS else 1.0
        Y = np.array(collection.get(prop, []), dtype=float) * scale
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
            centers = np.array(r["_hist_centers"]) * scale
            x_fine = np.linspace(centers[0], centers[-1], 200)
            y_fine = float(np.array(r["_hist_counts"]).max()) * np.exp(
                -((x_fine - r["MEAN"] * scale) ** 2) / (2 * (r["STD"] * scale) ** 2)
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
                x0=r.get("MEAN", 0) * scale,
                x1=r.get("MEAN", 0) * scale,
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


def _render_compare_section() -> None:
    st.divider()
    st.subheader("Compare experiments")

    eligible = []
    for j in list_completed_jobs():
        _, _, out = job_dirs(j["job_id"])
        if (out / "population.json").is_file() and (
            out / "collection_postprocessed.json"
        ).is_file():
            eligible.append(j)

    if len(eligible) < 2:
        st.info(
            "Run population analysis on at least 2 experiments to compare them here."
        )
        return

    labels = {j["job_id"]: j.get("name") or j["job_id"] for j in eligible}
    selected = st.multiselect(
        "Experiments to compare",
        [j["job_id"] for j in eligible],
        format_func=lambda x: labels[x],
        max_selections=3,
        key="compare_jobs",
    )
    if len(selected) < 2:
        st.info("Select 2–3 experiments.")
        return

    loaded = {}
    for jid in selected:
        _, _, out = job_dirs(jid)
        loaded[jid] = (
            json.loads((out / "population.json").read_text()),
            json.loads((out / "collection_postprocessed.json").read_text()),
        )

    common_props = set(loaded[selected[0]][0]["properties"])
    for jid in selected[1:]:
        common_props &= set(loaded[jid][0]["properties"])
    common_props = [p for p in AVAILABLE_PROPS if p in common_props]
    if not common_props:
        st.warning("No common properties across the selected experiments.")
        return

    props = st.multiselect(
        "Properties",
        common_props,
        default=common_props,
        key="compare_props",
    )
    if not props:
        return

    keys = ["STD", "MEAN"]
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Property": f"{p} (µ)" if p in MICRO_PROPS else p,
                    **{
                        f"{k} - {labels[jid]}": _display_val(
                            p,
                            k,
                            loaded[jid][0]["results"].get(p, {}).get(k, float("nan")),
                        )
                        for k in keys
                        for jid in selected
                    },
                }
                for p in props
            ],
        ),
        hide_index=True,
        use_container_width=True,
    )

    titles = [f"{p} (µ)" if p in MICRO_PROPS else p for p in props]
    fig = sp.make_subplots(rows=1, cols=len(props), subplot_titles=titles)
    for col, prop in enumerate(props, 1):
        scale = 1e6 if prop in MICRO_PROPS else 1.0
        series = {}
        for jid in selected:
            Y = (
                np.array(loaded[jid][1]["collection"].get(prop, []), dtype=float)
                * scale
            )
            series[jid] = Y[~np.isnan(Y)]
        all_vals = (
            np.concatenate([Y for Y in series.values() if len(Y)])
            if any(len(Y) for Y in series.values())
            else np.array([])
        )
        if not len(all_vals):
            continue
        xbins = {
            "start": float(all_vals.min()),
            "end": float(all_vals.max()),
            "size": (float(all_vals.max()) - float(all_vals.min())) / 20 or 1.0,
        }
        for i, jid in enumerate(selected):
            if not len(series[jid]):
                continue
            fig.add_trace(
                go.Histogram(
                    x=series[jid],
                    xbins=xbins,
                    marker_color=_COMPARE_COLORS[i % len(_COMPARE_COLORS)],
                    opacity=0.55,
                    name=labels[jid],
                    legendgroup=str(jid),
                    showlegend=col == 1,
                ),
                row=1,
                col=col,
            )
    fig.update_layout(
        height=300,
        margin={"l": 40, "r": 20, "t": 40, "b": 40},
        barmode="overlay",
        bargap=0.05,
    )
    st.plotly_chart(fig, use_container_width=True)


def _save_population(
    out: Path, result: dict, method: str, props: list[str], n_kept: int | None
) -> None:
    (out / "population.json").write_text(
        u.to_json(
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
        )
    )

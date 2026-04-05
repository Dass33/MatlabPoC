"""
Here users choose from a dropdown of experiments
which already came through the matlab pipline,
they can analyse the resulst -> look at the tracks,kymographs,
if they are satisfied they will go to the other tab,
if they are not they will go back to the submit tab and change paramters
and resubmit.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go
import scipy.io
from job_manager import job_dirs
from results import list_kymographs, render_kymographs

import streamlit as st


def page_kymograph_analysis(job_id: str | None) -> None:
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    _, _, out = job_dirs(job_id)

    col_kymo, col_scatter = st.columns([1, 1])

    with col_kymo:
        st.subheader("Kymographs")
        kymographs = list_kymographs(out)
        render_kymographs(kymographs, job_id, key_suffix="kymo_tab")

    with col_scatter:
        st.subheader("Trajectories")
        _render_trajectory_scatter(job_id, out)


def _render_trajectory_scatter(job_id: str, out) -> None:

    collection = _load_collection_scalars(out)
    if collection is None:
        st.warning(
            "collection.mat not found — kymograph analysis may still be running."
        )
        return

    props = [
        k for k, v in collection.items() if isinstance(v, np.ndarray) and v.ndim == 1
    ]
    if len(props) < 2:
        st.info("Not enough scalar properties to plot.")
        return

    default_x = "iOC" if "iOC" in props else props[0]
    default_y = "velocity" if "velocity" in props else props[1]

    col_x, col_y = st.columns(2)
    with col_x:
        x_prop = st.selectbox(
            "X axis", props, index=props.index(default_x), key=f"kymo_x_{job_id}"
        )
    with col_y:
        y_prop = st.selectbox(
            "Y axis", props, index=props.index(default_y), key=f"kymo_y_{job_id}"
        )

    x = collection[x_prop]
    y = collection[y_prop]
    n_traj = len(x)

    fig = go.Figure(
        go.Scatter(
            x=x,
            y=y,
            mode="markers",
            marker={"size": 8, "color": "#0072B2"},
            text=[f"Trajectory {i}" for i in range(n_traj)],
            hovertemplate=f"{x_prop}: %{{x:.4f}}<br>{y_prop}: %{{y:.4f}}<extra>%{{text}}</extra>",
        )
    )
    fig.update_layout(
        xaxis_title=x_prop,
        yaxis_title=y_prop,
        margin={"l": 40, "r": 20, "t": 20, "b": 40},
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"{n_traj} trajectories")


def _load_collection_scalars(out) -> dict | None:
    mat_path = Path(out) / "collection" / "collection.mat"
    if not mat_path.exists():
        return None

    m = scipy.io.loadmat(str(mat_path), squeeze_me=True)
    c = m["collection"]
    result = {}
    for f in c.dtype.names:
        v = c[f].item()
        if (
            isinstance(v, np.ndarray)
            and v.ndim == 1
            and np.issubdtype(v.dtype, np.number)
        ):
            result[f] = v
    return result

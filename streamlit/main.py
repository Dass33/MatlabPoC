"""
NSM Data Processing — Streamlit frontend.

Environment variables (set in docker-compose / .env)
─────────────────────────────────────────────────────
  DATA_DIR          base path for jobs inside container  (default: /data/jobs)
  HOST_DATA_DIR     same path as seen by the host daemon (required)
  MATLAB_IMAGE      Docker image name                    (default: matlab-algorithm:latest)
  POLL_INTERVAL_S   seconds between status polls         (default: 5)
"""

from __future__ import annotations

import logging

from config import render_config_sidebar
from help import page_help
from history import page_history
from job_manager import list_completed_jobs
from kymograph import page_kymograph_analysis
from population import page_population_analysis
from postprocessing import page_postprocessing
from submit import page_submit

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────


def main() -> None:
    st.set_page_config(
        page_title="NSM Data Processing",
        page_icon="🔬",
        layout="wide",
        initial_sidebar_state="auto",
        menu_items={"About": "NSM data processing — Streamlit frontend"},
    )

    st.session_state.setdefault("last_job_id", None)
    st.session_state.setdefault("waiting", False)
    st.session_state.setdefault("active_experiment", None)

    config = render_config_sidebar()

    render_experiment_selector()

    (
        tab_submit,
        tab_kymograph,
        tab_postprocessing,
        tab_population,
        tab_history,
        tab_help,
    ) = st.tabs([
        "Submit",
        "Kymograph Analysis",
        "Post-processing",
        "Population Analysis",
        "History",
        "Help",
    ])

    active_job = st.session_state.get("active_experiment")

    with tab_submit:
        page_submit(config)

    with tab_kymograph:
        page_kymograph_analysis(active_job)

    with tab_postprocessing:
        page_postprocessing(active_job)

    with tab_population:
        page_population_analysis(active_job)

    with tab_history:
        page_history()

    with tab_help:
        page_help()


def render_experiment_selector() -> None:
    completed = list_completed_jobs()
    if not completed:
        return

    options = [j["job_id"] for j in completed]
    labels  = {j["job_id"]: j.get("name") or j["job_id"] for j in completed}

    st.selectbox(
        "Active experiment",
        options,
        format_func=lambda x: labels[x],
        key="active_experiment",
    )
    st.divider()


if __name__ == "__main__":
    main()

"""NSM Data Processing — Streamlit frontend.

Environment variables (set in docker-compose / .env):
  DATA_DIR          base path for jobs inside container  (default: /data/jobs)
  POLL_INTERVAL_S   seconds between status polls         (default: 5)
  MCR_ROOT          MATLAB runtime root                  (default: /opt/matlabruntime/R2025b)
  MATLAB_APP        path to run_AnalyzeExperimentApp.sh  (default: /opt/matlab_app/...)
"""

from __future__ import annotations

import logging

import streamlit as st

from config import render_config_sidebar
from connectors.storage import list_completed_jobs
from tabs.help import page_help
from tabs.history import page_history
from tabs.kymograph import page_kymograph_analysis
from tabs.population import page_population_analysis
from tabs.postprocessing import page_postprocessing
from tabs.submit import page_submit

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)


def main() -> None:
    """Application entry point. Renders sidebar config, experiment selector, and tabbed UI."""
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
    """Dropdown at the top of the page to pick a completed experiment."""
    completed = list_completed_jobs()
    if not completed:
        return

    options = [j["job_id"] for j in completed]
    labels = {j["job_id"]: j.get("name") or j["job_id"] for j in completed}

    st.selectbox(
        "Active experiment",
        options,
        format_func=lambda x: labels[x],
        key="active_experiment",
    )
    st.divider()


if __name__ == "__main__":
    main()

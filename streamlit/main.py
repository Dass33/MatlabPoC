"""NSM Data Processing — Streamlit frontend.

Environment variables (set in docker-compose / .env):
  DATA_DIR          base path for jobs inside container  (default: /data/jobs)
  POLL_INTERVAL_S   seconds between status polls         (default: 5)
  MCR_ROOT          MATLAB runtime root                  (default: /opt/matlabruntime/R2025b)
  MATLAB_APP        path to run_AnalyzeExperimentApp.sh  (default: /opt/matlab_app/...)
"""

from __future__ import annotations

import json
import logging
import threading

from config import active_preset, apply_settings, render_config_sidebar
from connectors import algorithms
from connectors.launcher import launch_matlab_job
from connectors.storage import clone_job, create_demo_job, list_completed_jobs
from env import DEMO_DATA_DIR, job_dirs
from preset_editor import page_preset_editor
from tabs.help import page_help
from tabs.kymograph import page_kymograph_analysis
from tabs.overview import page_overview
from tabs.population import page_population_analysis
from tabs.postprocessing import page_postprocessing
from tabs.submit import page_submit

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

st.set_page_config(
    page_title="NSM Data Processing",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "NSM data processing — Streamlit frontend"},
)

st.html("style.css")


@st.cache_resource
def _warm_mcr() -> bool:
    """Kick off MCR init in the background, once per process."""
    threading.Thread(target=algorithms.warm_up, daemon=True).start()
    return True


def main() -> None:
    """Application entry point. Renders sidebar config, experiment selector, and tabbed UI."""
    _warm_mcr()

    st.session_state.setdefault("last_job_id", None)
    st.session_state.setdefault("waiting", False)
    st.session_state.setdefault("active_experiment", None)
    st.session_state.setdefault("_tour_seen", False)

    if st.query_params.get("preset-editor") == "on":
        page_preset_editor()
        return

    pending = st.session_state.get("_clone_pending")
    if pending and pending["use_original"]:
        base, _, _ = job_dirs(pending["source_job_id"])
        config_file = base / "config.json"
        preset = active_preset()
        if config_file.is_file() and preset:
            apply_settings(preset, json.loads(config_file.read_text()))

    config = render_config_sidebar()

    if pending := st.session_state.pop("_clone_pending", None):
        new_id = clone_job(pending["source_job_id"], config, name=pending["name"])
        launch_matlab_job(new_id)
        st.session_state["last_job_id"] = new_id
        st.session_state["_submit_toast"] = f"Cloned as `{new_id}` — submitted."

    render_tour_banner(config)
    render_experiment_selector()

    (
        tab_submit,
        tab_kymograph,
        tab_postprocessing,
        tab_population,
        tab_overview,
        tab_help,
    ) = st.tabs([
        "Submit",
        "Kymograph Analysis",
        "Post-processing",
        "Population Analysis",
        "Overview",
        "Help",
    ])

    active_job = st.session_state.get("active_experiment") or st.session_state.get(
        "last_job_id"
    )

    with tab_submit:
        page_submit(config)

    with tab_kymograph:
        page_kymograph_analysis(active_job)

    with tab_postprocessing:
        page_postprocessing(active_job)

    with tab_population:
        page_population_analysis(active_job)

    with tab_overview:
        page_overview()

    with tab_help:
        page_help()


def render_tour_banner(config) -> None:
    """First-run banner walking a new user through the pipeline unattended."""
    if st.query_params.get("tutorial") != "on":
        return

    with st.container(border=True):
        st.markdown(
            """
            **New here?**
            1. **Submit** tab → click **Load demo dataset** (or upload your own TIFF+txt pairs).
            2. Wait for it to finish (or toggle **Wait for result** to watch progress).
            3. **Post-processing** tab → review the scatter/thresholds, then **Accept & Save**.
            4. **Population Analysis** tab → click **Run Population Analysis**.
            5. Compare it against another experiment, or download results from **Overview**.

            Look at the [Documentation](https://dass33.github.io/MatlabPoC/)
            """
        )
        load_demo, show_tutorial = st.columns([1, 5])
        with load_demo:
            if any(DEMO_DATA_DIR.glob("*")) and st.button(
                "Run demo dataset",
                help="Run a bundled example experiment.",
                key="run_demo",
            ):
                with st.spinner("Loading demo dataset..."):
                    job_id = create_demo_job(config)
                launch_matlab_job(job_id)
                st.session_state["last_job_id"] = job_id
                st.session_state["_submit_toast"] = f"Demo job submitted — `{job_id}`"
                st.rerun()

        with show_tutorial:
            if st.button("Got it, don't show again", key="show_tutorial"):
                st.query_params.pop("tutorial")
                st.rerun()


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


if __name__ == "__main__":
    main()

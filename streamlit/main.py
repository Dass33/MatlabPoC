"""
NSM Data Processing — Streamlit frontend.

Job lifecycle
─────────────
  /data/jobs/{job_id}/
      input/          ← TIFF(s) written by Streamlit (streamed, not buffered)
      config.json     ← algorithm parameters
      output/         ← results written by MATLAB container

status.json schema
──────────────────
  { "status": "processing" | "completed" | "failed", "error": "<msg or null>" }

MATLAB container is invoked via the Docker socket:
  docker run --rm -v /host/path/{job_id}:/job {MATLAB_IMAGE} /job/input /job/output
  Config is read by MATLAB from /job/config.json.

Environment variables (set in docker-compose / .env)
─────────────────────────────────────────────────────
  DATA_DIR          base path for jobs inside container  (default: /data/jobs)
  HOST_DATA_DIR     same path as seen by the host daemon (required)
  MATLAB_IMAGE      Docker image name                    (default: matlab-algorithm:latest)
  MAX_WORKERS       concurrent MATLAB slots              (default: 2)
  POLL_INTERVAL_S   seconds between status polls         (default: 5)
"""

from __future__ import annotations

import logging

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from config import render_config_sidebar
from help import page_help
from history import page_history
from submit import page_submit

STATUS_ICON = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}

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

    config = render_config_sidebar()

    tab_submit, tab_history, tab_help = st.tabs(["Submit", "History", "Help"])

    with tab_submit:
        page_submit(config)

    with tab_history:
        page_history()

    with tab_help:
        page_help()


if __name__ == "__main__":
    main()

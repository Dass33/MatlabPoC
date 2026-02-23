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

import json
import logging
import time
from pathlib import Path

import pandas as pd
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from config import render_config_sidebar
from job_manager import (
    DATA_DIR,
    MAX_WORKERS,
    POLL_INTERVAL_S,
    count_running_jobs,
    job_dirs,
    list_all_jobs,
    read_status,
    submit_job,
)
from results import _render_kymographs, _show_job_results, list_kymographs

STATUS_ICON = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}


# ─────────────────────────────────────────────
# Page: Submit
# ─────────────────────────────────────────────


def page_submit(config: dict) -> None:
    st.header("Submit Analysis")

    uploaded_files = st.file_uploader(
        "Upload .tiff files and their paired .txt metadata files",
        type=["tif", "tiff", "txt"],
        accept_multiple_files=True,
        key="uploader",
    )

    running = count_running_jobs()
    slots_free = MAX_WORKERS - running
    slots_colour = "green" if slots_free > 0 else "red"
    st.markdown(
        f"**Worker slots:** :{slots_colour}[{slots_free} / {MAX_WORKERS} available]"
    )

    if not uploaded_files:
        st.info(
            "Upload one or more .tiff files and their paired .txt metadata files to begin."
        )
        return

    tiff_stems = {
        Path(f.name).stem
        for f in uploaded_files
        if f.name.lower().endswith((".tif", ".tiff"))
    }
    txt_stems = {
        Path(f.name).stem for f in uploaded_files if f.name.lower().endswith(".txt")
    }
    missing_txt = tiff_stems - txt_stems
    if missing_txt:
        st.error(
            f"Missing paired .txt metadata file(s) for: {', '.join(sorted(missing_txt))}. "
            "Each .tiff must have a matching .txt with the same base name."
        )
        return

    col_submit, col_wait = st.columns(2)
    with col_submit:
        submit = st.button(
            "Submit job",
            type="primary",
            disabled=(slots_free == 0),
            width="stretch",
        )
    with col_wait:
        wait_for_result = st.toggle("Wait for result", value=False)

    if slots_free == 0:
        st.warning(
            "Both worker slots are busy. "
            "Submit your job once a slot is free, or check the History tab."
        )

    if submit:
        with st.spinner("Writing files to disk..."):
            try:
                job_id = submit_job(uploaded_files, config)
            except Exception as e:
                st.error(f"Failed to submit job: {e}")
                return

        st.success(f"Job submitted — ID: `{job_id}`")
        st.session_state["last_job_id"] = job_id
        st.session_state["waiting"] = wait_for_result

    active_job_id = st.session_state.get("last_job_id")
    if active_job_id and st.session_state.get("waiting"):
        status_placeholder = st.empty()
        result_placeholder = st.empty()

        status = read_status(active_job_id)
        if status["status"] == "processing":
            status_placeholder.info(
                f"Running... (job `{active_job_id}`). Checking every {POLL_INTERVAL_S}s."
            )
            time.sleep(POLL_INTERVAL_S)
            st.rerun()
        else:
            st.session_state["waiting"] = False
            status_placeholder.empty()
            if status["status"] == "completed":
                result_placeholder.success("Analysis complete!")
                _show_job_results(active_job_id, key_suffix="submit")
            else:
                result_placeholder.error(
                    f"Job failed: {status.get('error', 'unknown error')}"
                )


# ─────────────────────────────────────────────
# Page: History
# ─────────────────────────────────────────────


def page_history() -> None:
    st.header("Experiment History")

    col_refresh, col_auto = st.columns([1, 3])
    with col_refresh:
        if st.button("Refresh", width="stretch"):
            st.rerun()
    with col_auto:
        auto_refresh = st.toggle("Auto-refresh every 10 s", value=False)

    jobs = list_all_jobs()

    if not jobs:
        st.info("No jobs found yet.")
        return

    st.dataframe(
        pd.DataFrame([
            {
                "Job ID": j["job_id"],
                "Files": ", ".join(j.get("filenames", [])),
                "Submitted": j.get("submitted_at", "—"),
                "Status": f"{STATUS_ICON.get(j['status'], '❓')} {j['status']}",
                "Error": j.get("error") or "" if j["status"] == "failed" else "",
            }
            for j in jobs
        ]),
        width="stretch",
        hide_index=True,
    )

    completed_jobs = [j for j in jobs if j["status"] == "completed"]
    if completed_jobs:
        st.divider()
        options = {
            j["job_id"]: f"{j['job_id']} — {', '.join(j['filenames'])}"
            for j in completed_jobs
        }
        selected_id = st.selectbox(
            "View results for job",
            options=list(options.keys()),
            format_func=lambda k: options[k],
        )
        if selected_id:
            _show_job_results(selected_id, key_suffix="history")
    else:
        st.caption("No completed jobs to display yet.")

    failed_jobs = [j for j in jobs if j["status"] == "failed"]
    if failed_jobs:
        st.divider()
        st.subheader("Failed jobs")
        options = {
            j["job_id"]: f"{j['job_id']} — {', '.join(j['filenames'])}"
            for j in failed_jobs
        }
        selected_failed = st.selectbox(
            "Select failed job",
            options=list(options.keys()),
            format_func=lambda k: options[k],
            key="failed_select",
        )
        if selected_failed:
            failed_job = next(j for j in failed_jobs if j["job_id"] == selected_failed)
            st.error(failed_job.get("error") or "Unknown error")
            _, _, out = job_dirs(selected_failed)
            kymographs = list_kymographs(out)
            if kymographs:
                st.caption("Kymographs generated before failure:")
                _render_kymographs(kymographs, selected_failed, key_suffix="failed")

    stuck_jobs = [j for j in jobs if j["status"] == "processing"]
    if stuck_jobs:
        with st.expander("Admin"):
            options = {
                j["job_id"]: f"{j['job_id']} — {', '.join(j['filenames'])}"
                for j in stuck_jobs
            }
            selected = st.selectbox(
                "Stuck job",
                options=list(options.keys()),
                format_func=lambda k: options[k],
                key="admin_select",
            )
            if st.button("Force free slot", key="admin_force"):
                _, _, out = job_dirs(selected)
                out.mkdir(parents=True, exist_ok=True)
                (out / "status.json").write_text(
                    json.dumps({"status": "failed", "error": "Manually freed by admin"})
                )
                st.rerun()

    if auto_refresh:
        time.sleep(10)
        st.rerun()


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
        st.markdown(f"""
        ### How to use

        1. Configure algorithm parameters in the sidebar.
        2. Upload your `.tiff` files **and their paired `.txt` metadata files** in the **Submit** tab.
           Each TIFF must have a matching TXT with the same base name (e.g. `data_001.tiff` + `data_001.txt`).
        3. Click **Submit job**. Files are written to disk immediately and the
           MATLAB container starts in the background — your browser does not need
           to stay open.
        4. Enable **Wait for result** if you prefer to watch progress on this page.
        5. Once complete, results appear in the **History** tab. All users share
           the same history.

        ### Output files

        | File | Contents |
        |------|----------|
        | `kymographs/*.png` | Kymograph images with track overlays |
        | `trajectories.mat` | Per-trajectory: iOC, D, velocity, N, positionStart, positionEnd |
        | `summary.json` | Population statistics per sweep (MEAN, FWHM, RESOLUTION) |
        | `results.mat` | Full archive for MATLAB post-processing |

        ### Parameter sweep

        Enable **Parameter sweep** in the sidebar to run multiple Wx × Wt combinations
        in a single job. Enter comma-separated values, e.g. `10, 15, 20`.

        ### Worker slots

        There are **{MAX_WORKERS}** concurrent MATLAB worker slots. If both are busy,
        wait for one to finish.

        ### File retention

        Input and output files are stored under `{DATA_DIR}`.
        """)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import logging
import time

import pandas as pd
import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from job_manager import (
    job_dirs,
    list_all_jobs,
)
from results import _render_kymographs, _show_job_results, list_kymographs

STATUS_ICON = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}

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

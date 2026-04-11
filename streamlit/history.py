from __future__ import annotations

import io
import json
import time
import zipfile
from pathlib import Path

import pandas as pd
from job_manager import STATUS_ICON, job_dirs, list_all_jobs

import streamlit as st


def page_history() -> None:
    st.subheader("Experiment History")

    col_refresh, col_auto = st.columns([1, 3])
    if col_refresh.button("Refresh", width="stretch"):
        st.rerun()
    auto_refresh = col_auto.toggle("Auto-refresh every 10 s", value=False)

    jobs = list_all_jobs()
    if not jobs:
        st.info("No jobs found yet.")
        return

    tiff_stems = lambda j: ", ".join(
        Path(f).stem for f in j.get("filenames", []) if f.lower().endswith((".tif", ".tiff"))
    )
    st.dataframe(
        pd.DataFrame([{
            "Name":      j.get("name") or j["job_id"],
            "Submitted": j.get("submitted_at", "—"),
            "Files":     tiff_stems(j),
            "Status":    f"{STATUS_ICON.get(j['status'], '❓')} {j['status']}",
        } for j in jobs]),
        width="stretch",
        hide_index=True,
    )

    completed_jobs = [j for j in jobs if j["status"] == "completed"]
    if completed_jobs:
        st.divider()
        st.subheader("Download results")
        labels     = {j["job_id"]: j.get("name") or j["job_id"] for j in completed_jobs}
        selected_id = st.selectbox("Job", [j["job_id"] for j in completed_jobs], format_func=lambda x: labels[x], key="history_download_select")
        if selected_id:
            st.download_button(
                "Download Results",
                data=_zip_results(selected_id),
                mime="application/zip",
                file_name=f"{labels[selected_id]}.zip",
            )

    failed_jobs = [j for j in jobs if j["status"] == "failed"]
    if failed_jobs:
        st.divider()
        st.subheader("Failed jobs")
        for j in failed_jobs:
            with st.expander(j.get("name") or j["job_id"]):
                st.error(j.get("error") or "Unknown error")

    stuck_jobs = [j for j in jobs if j["status"] == "processing"]
    if stuck_jobs:
        st.divider()
        with st.expander("Admin — stuck jobs"):
            labels_stuck = {j["job_id"]: j.get("name") or j["job_id"] for j in stuck_jobs}
            selected = st.selectbox("Stuck job", [j["job_id"] for j in stuck_jobs], format_func=lambda x: labels_stuck[x], key="admin_select")
            if st.button("Mark as failed", key="admin_force"):
                _, _, out = job_dirs(str(selected))
                out.mkdir(parents=True, exist_ok=True)
                (out / "status.json").write_text(json.dumps({"status": "failed", "error": "Manually freed by admin"}))
                st.rerun()

    if auto_refresh:
        time.sleep(10)
        st.rerun()


def _zip_results(job_id: str) -> bytes:
    base, _, out = job_dirs(job_id)
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        config = base / "config.json"
        if config.is_file():
            zf.write(config, "config.json")

        kymo_dir = out / "kymographs"
        if kymo_dir.is_dir():
            for f in sorted(kymo_dir.glob("*.png")):
                zf.write(f, Path("kymographs") / f.name)

        for name in ("collection/collection.mat", "collection_postprocessed.json", "population.json"):
            p = out / name
            if p.is_file():
                zf.write(p, name)

        setting = out / "Setting.json"
        if setting.is_file():
            zf.write(setting, "Setting.json")

    return buffer.getvalue()

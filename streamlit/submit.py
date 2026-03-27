from __future__ import annotations

import logging
import time
from pathlib import Path

import streamlit as st

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

from job_manager import (
    MAX_WORKERS,
    POLL_INTERVAL_S,
    count_running_jobs,
    read_status,
    submit_job,
)
from results import show_job_results

STATUS_ICON = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}

UPLOADER_CLEAR = "uploader_clear"
UPLOADER = "uploader_"


# ─────────────────────────────────────────────
# Page: Submit
# ─────────────────────────────────────────────


def page_submit(config: dict) -> None:
    st.header("Submit Analysis")

    # We do this to be able to have clear all files button
    if UPLOADER_CLEAR not in st.session_state:
        st.session_state[UPLOADER_CLEAR] = 0

    uploaded_files = st.file_uploader(
        "Upload .tiff files and their paired .txt metadata files",
        type=["tif", "tiff", "txt"],
        accept_multiple_files=True,
        key=get_uploader_key(),
    )

    st.button(
        label="Clear uploaded files", key="Clear files button", on_click=clear_uploader
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
                dark_cal_bytes = st.session_state.get("dark_cal_bytes")
                job_id = submit_job(uploaded_files, config, dark_cal_bytes=dark_cal_bytes)
            except Exception as e:  # noqa: BLE001
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
                show_job_results(active_job_id, key_suffix="submit")
            else:
                result_placeholder.error(
                    f"Job failed: {status.get('error', 'unknown error')}"
                )

    missing_txt = tiff_stems - txt_stems
    if missing_txt:
        st.error(
            f"Missing paired .txt metadata file(s) for: {', '.join(sorted(missing_txt))}. "
            "Each .tiff must have a matching .txt with the same base name."
        )

    st.divider()
    show_all_uploaded()


def get_uploader_key():
    return f"{UPLOADER}{st.session_state[UPLOADER_CLEAR]}"


def clear_uploader():
    st.session_state[UPLOADER_CLEAR] += 1


def show_all_uploaded():
    uploaded_files = st.session_state[get_uploader_key()]
    with st.expander(label="List of all uploaded files"):
        for f in uploaded_files:
            st.write(f.name)

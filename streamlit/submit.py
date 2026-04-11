from __future__ import annotations

import time
from pathlib import Path

from job_manager import (
    POLL_INTERVAL_S,
    read_status,
    submit_job,
)

import streamlit as st

UPLOADER_CLEAR = "uploader_clear"
UPLOADER = "uploader_"


def page_submit(config: dict) -> None:
    st.subheader("Submit Analysis")

    if toast_msg := st.session_state.pop("_submit_toast", None):
        st.toast(toast_msg)

    if UPLOADER_CLEAR not in st.session_state:
        st.session_state[UPLOADER_CLEAR] = 0

    name = st.text_input(
        "Experiment name", placeholder="optional label for this run", key="job_name"
    )

    uploaded_files = st.file_uploader(
        "Upload .tiff files and their paired .txt metadata files",
        type=["tif", "tiff", "txt"],
        accept_multiple_files=True,
        key=_uploader_key(),
    )
    st.button(
        "Clear uploaded files", key="Clear files button", on_click=_clear_uploader
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
    submit = col_submit.button(
        "Submit job", type="primary", width="stretch"
    )
    wait_for_result = col_wait.toggle("Wait for result", value=False)

    if submit:
        with st.spinner("Writing files to disk..."):
            try:
                job_id = submit_job(
                    uploaded_files,
                    config,
                    dark_cal_bytes=st.session_state.get("dark_cal_bytes"),
                    name=name,
                )
            except Exception as e:
                st.error(f"Failed to submit job: {e}")
                return
        st.session_state["last_job_id"] = job_id
        st.session_state["waiting"] = wait_for_result
        if not wait_for_result:
            st.session_state["_submit_toast"] = f"Job submitted — `{job_id}`"
            st.rerun()

    active_job_id = st.session_state.get("last_job_id")
    if active_job_id and st.session_state.get("waiting"):
        status_placeholder = st.empty()
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
                st.success(
                    "Analysis complete! View results in the **Kymograph Analysis** tab."
                )
            else:
                st.error(f"Job failed: {status.get('error', 'unknown error')}")
            st.rerun()

    missing_txt = tiff_stems - txt_stems
    if missing_txt:
        st.error(
            f"Missing paired .txt metadata file(s) for: {', '.join(sorted(missing_txt))}. Each .tiff must have a matching .txt with the same base name."
        )

    st.divider()
    with st.expander("List of all uploaded files"):
        for f in uploaded_files:
            st.write(f.name)


def _uploader_key():
    return f"{UPLOADER}{st.session_state[UPLOADER_CLEAR]}"


def _clear_uploader():
    st.session_state[UPLOADER_CLEAR] += 1

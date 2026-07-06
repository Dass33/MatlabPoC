from __future__ import annotations

from pathlib import Path

import streamlit as st

from connectors.launcher import launch_matlab_job
from connectors.storage import create_job, read_status
from env import POLL_INTERVAL_S, job_dirs

PNG_EOF = b"IEND\xaeB\x60\x82"

UPLOADER_CLEAR = "uploader_clear"
UPLOADER = "uploader_"


def page_submit(config: dict) -> None:
    """Submit tab — upload TIFF/TXT files, configure job, and launch MATLAB analysis."""
    st.subheader("Submit Analysis")

    if toast_msg := st.session_state.pop("_submit_toast", None):
        st.toast(toast_msg)

    if result := st.session_state.pop("_submit_result", None):
        kind, msg = result
        (st.success if kind == "success" else st.error)(msg)

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
    submit = col_submit.button("Submit job", type="primary", width="stretch")
    wait_for_result = col_wait.toggle("Wait for result", value=False)

    if submit:
        with st.spinner("Writing files to disk..."):
            try:
                job_id = create_job(
                    uploaded_files,
                    config,
                    dark_cal_bytes=st.session_state.get("dark_cal_bytes"),
                    name=name,
                )
            except OSError as e:
                st.error(f"Failed to write files: {e}")
                return
        launch_matlab_job(job_id)
        st.session_state["last_job_id"] = job_id
        st.session_state["waiting"] = wait_for_result
        if not wait_for_result:
            st.session_state["_submit_toast"] = f"Job submitted — `{job_id}`"
            st.rerun()

    active_job_id = st.session_state.get("last_job_id")
    if active_job_id and st.session_state.get("waiting"):
        _wait_for_result(active_job_id)

    missing_txt = tiff_stems - txt_stems
    if missing_txt:
        st.error(
            f"Missing paired .txt metadata file(s) for: {', '.join(sorted(missing_txt))}. Each .tiff must have a matching .txt with the same base name."
        )

    st.divider()
    with st.expander("List of all uploaded files"):
        for f in uploaded_files:
            st.write(f.name)


@st.fragment(run_every=POLL_INTERVAL_S)
def _wait_for_result(job_id: str) -> None:
    """Poll job status without blocking the rest of the app. On a terminal status it
    stashes the outcome and triggers a full rerun, which stops this fragment's loop."""
    status = read_status(job_id)
    if status["status"] == "processing":
        st.info(
            f"Running... (job `{job_id}`). Auto-refreshing every {POLL_INTERVAL_S}s."
        )
        _render_partial_kymographs(job_id)
        return
    st.session_state["waiting"] = False
    if status["status"] == "completed":
        st.session_state["_submit_result"] = (
            "success",
            "Analysis complete! View results in the **Kymograph Analysis** tab.",
        )
    else:
        st.session_state["_submit_result"] = (
            "error",
            f"Job failed: {status.get('error', 'unknown error')}",
        )
    st.rerun()


def _render_partial_kymographs(job_id: str) -> None:
    _, _, out = job_dirs(job_id)
    pngs = sorted((out / "kymographs").glob("*.png"))
    if not pngs:
        return
    st.caption(f"{len(pngs)} kymograph(s) so far")
    for f in pngs:
        try:
            data = f.read_bytes()
        except OSError:
            continue
        # MATLAB may still be mid-write; only render PNGs with a complete IEND chunk.
        if data.endswith(PNG_EOF):
            st.image(data, caption=f.name, use_container_width=True)


def _uploader_key() -> str:
    return f"{UPLOADER}{st.session_state[UPLOADER_CLEAR]}"


def _clear_uploader() -> None:
    st.session_state[UPLOADER_CLEAR] += 1

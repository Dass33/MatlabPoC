"""
NSM Data Processing — Streamlit frontend.

Job lifecycle
─────────────
  /data/jobs/{job_id}/
      input/          ← TIFF(s) written by Streamlit (streamed, not buffered)
      config.json     ← algorithm parameters
      output/         ← .mat file(s) + status.json written by MATLAB container

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
  MATLAB_IMAGE      Docker image name                    (default: nsm-matlab:latest)
  MAX_WORKERS       concurrent MATLAB slots              (default: 2)
  POLL_INTERVAL_S   seconds between status polls         (default: 5)
"""

from __future__ import annotations

import json
import os
import shutil
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import docker
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
import tifffile

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data/jobs"))
# HOST_DATA_DIR must match DATA_DIR as seen by the host Docker daemon.
# The daemon runs on the host, not inside the Streamlit container, so it
# cannot resolve container-internal paths.
HOST_DATA_DIR = Path(os.environ.get("HOST_DATA_DIR", str(DATA_DIR)))
MATLAB_IMAGE = os.environ.get("MATLAB_IMAGE", "nsm-matlab:latest")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "5"))

DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default algorithm parameters — single source of truth.
# MATLAB reads these from config.json and has no defaults of its own.
DEFAULT_CONFIG: dict[str, Any] = {
    # Preprocessing
    "Kt": 159.0,
    # Denoising
    "spaceFilter": "jinc",
    "sigma_x": 2.97,
    "timeFilter": "imgaussfilt",
    "sigma_t": 1.19,
    "nonLinearFilter": "none",
    # Detection
    "pfa": 1e-5,
    "localMinRange": 6,
    # Feature extraction
    "positionRefinementMethod": "centroid",
    "fittingRadius": 3,
    # Contrast image (internal pipeline parameters, not exposed in UI)
    "Contrast_chainOrder": "preprocessing_denoising",
    "Contrast_defluctuationMethod": "mean",
    "Contrast_Kx": 1,
    "Contrast_bacgroundEstimationMethod": "movmean",
    "Contrast_Kt": 159,
    "Contrast_backgroundRemovalMethod": "subtract_divide",
    "Contrast_whiteningMethod": "std_division",
    "Contrast_spaceFilter": "jinc",
    "Contrast_sigma_x": 2.97,
    "Contrast_k_max": 2,
    # Linking
    "cut_off_distance": 20.0,
    "unmatched_penalty_distance": 15.0,
    "flowEstimate": 0.0,
    "maxPositiveGab": 3.0,
    "maxNegativeGab": 2.0,
    "gab_closing_cut_off_distance": 40.0,
    "gab_closing_penalty_distance": 30.0,
    "minTrackLength": 40.0,
}

# ─────────────────────────────────────────────
# Job helpers
# ─────────────────────────────────────────────


def job_dirs(job_id: str) -> tuple[Path, Path, Path]:
    base = DATA_DIR / job_id
    return base, base / "input", base / "output"


def read_status(job_id: str) -> dict:
    _, _, out = job_dirs(job_id)
    status_file = out / "status.json"
    if not status_file.exists():
        return {"status": "processing", "error": None}
    try:
        return json.loads(status_file.read_text())
    except Exception:
        return {"status": "unknown", "error": "Could not read status.json"}


def count_running_jobs() -> int:
    if not DATA_DIR.exists():
        return 0
    return sum(
        1
        for d in DATA_DIR.iterdir()
        if d.is_dir() and read_status(d.name)["status"] == "processing"
    )


def list_all_jobs() -> list[dict]:
    """Return all jobs sorted newest first."""
    jobs = []
    if not DATA_DIR.exists():
        return jobs
    for job_dir in DATA_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        meta_file = job_dir / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text())
            status = read_status(job_dir.name)
            meta["status"] = status["status"]
            meta["error"] = status.get("error")
            jobs.append(meta)
        except Exception:
            continue
    return sorted(jobs, key=lambda j: j.get("submitted_at", ""), reverse=True)


def stream_upload_to_disk(uploaded_file, dest_path: Path) -> None:
    """
    Write a Streamlit UploadedFile to disk in chunks without buffering
    the whole file in RAM.
    """
    uploaded_file.seek(0)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f, length=8 * 1024 * 1024)  # 8 MB chunks


def launch_matlab_container(job_id: str) -> None:
    """
    Fire-and-forget: start the MATLAB container via the Docker socket.
    The entire job directory is mounted as /job so MATLAB can reach
    config.json, read from /job/input, and write to /job/output.
    """
    _, _, out = job_dirs(job_id)
    out.mkdir(parents=True, exist_ok=True)

    host_job_base = HOST_DATA_DIR / job_id

    print(f"[launch] image={MATLAB_IMAGE} host_job={host_job_base}", flush=True)

    client = docker.from_env()
    try:
        container = client.containers.run(
            MATLAB_IMAGE,
            command=["/opt/matlabruntime/R2025b", "/job/input", "/job/output"],
            volumes={str(host_job_base): {"bind": "/job", "mode": "rw"}},
            detach=True,
            remove=True,
        )
        print(f"[launch] container started: {container.short_id}", flush=True)
    except Exception as e:
        print(f"[launch] ERROR: {e}", flush=True)
        raise


def submit_job(uploaded_files: list, config: dict) -> str:
    """
    Stream uploaded files to disk, write metadata and config, then
    launch the MATLAB container. Returns the new job_id.
    """
    job_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    base, inp, out = job_dirs(job_id)
    inp.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    filenames = []
    for uf in uploaded_files:
        stream_upload_to_disk(uf, inp / uf.name)
        filenames.append(uf.name)

    (base / "config.json").write_text(json.dumps(config, indent=2))
    (base / "meta.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "filenames": filenames,
                "submitted_at": datetime.now().isoformat(timespec="seconds"),
            },
            indent=2,
        )
    )

    launch_matlab_container(job_id)
    return job_id


# ─────────────────────────────────────────────
# Results loading
# ─────────────────────────────────────────────


def _load_mat_h5(mat_path: Path) -> dict:
    """Load a MATLAB v7.3 .mat file (HDF5 format) using h5py."""
    import h5py

    def _flat(ds):
        return np.array(ds).flatten()

    with h5py.File(str(mat_path), "r") as f:
        det = f["Detections"]
        det_frames = _flat(det["frame"]) - 1
        det_positions = _flat(det["position"]) - 1
        det_positions_refined = _flat(det["position_refined"]) - 1
        contrast = _flat(det["contrast"])
        snr = _flat(det["snr"]) if "snr" in det else None

        # h5py reads MATLAB arrays transposed (row-major vs column-major)
        Y = np.array(f["Y"]).T if "Y" in f else np.array([])
        C = np.array(f["C"]).T if "C" in f else np.array([])

        ft = f["FinalTracks"] if "FinalTracks" in f else None
        final_tracks = None
        if ft is not None:
            n_tracks = int(np.array(ft["nTracks"]).item())
            frames_list, positions_list = [], []
            if n_tracks > 0:
                for ref in ft["frames"][0]:
                    frames_list.append(np.array(f[ref]).flatten())
                for ref in ft["positions_refined"][0]:
                    positions_list.append(np.array(f[ref]).flatten())
                # Note: track frame/position arrays are 1D so no transpose needed
            final_tracks = {
                "nTracks": n_tracks,
                "frames": frames_list,
                "positions_refined": positions_list,
            }

    return {
        "det_frames": det_frames,
        "det_positions": det_positions,
        "det_positions_refined": det_positions_refined,
        "det_contrast": contrast,
        "det_snr": snr,
        "denoised_y": Y,
        "contrast_c": C,
        "final_tracks": final_tracks,
    }


def load_mat_results(mat_path: Path) -> dict | None:
    """Load a .mat file (v7.3 / HDF5) and return a normalised results dict."""
    try:
        return _load_mat_h5(mat_path)
    except Exception as e:
        st.error(f"Could not load {mat_path.name}: {e}")
        return None


# ─────────────────────────────────────────────
# Visualisation
# ─────────────────────────────────────────────


def render_results(results: dict, raw_data: np.ndarray | None = None) -> None:
    det_frames = results["det_frames"]
    det_positions = results["det_positions"]
    det_positions_refined = results["det_positions_refined"]
    denoised_y = results["denoised_y"]
    contrast_c = results["contrast_c"]
    final_tracks = results["final_tracks"]

    pw, ph = 12, 7

    tab_labels = ["Tracks", "Denoised (Y)", "Contrast (C)"]
    if raw_data is not None:
        tab_labels.append("Raw (R)")
    tabs = st.tabs(tab_labels)

    # ── Tracks ──────────────────────────────────
    with tabs[0]:
        fig, ax = plt.subplots(figsize=(pw, ph))
        im = ax.imshow(-denoised_y, aspect="auto", cmap="viridis", origin="lower")
        n_tracks = 0
        if final_tracks is not None:
            try:
                n_tracks = int(final_tracks["nTracks"])
                frames_data = final_tracks["frames"]
                pos_data = final_tracks["positions_refined"]
                for i in range(n_tracks):
                    ax.plot(
                        np.array(pos_data[i]).flatten() - 1,
                        np.array(frames_data[i]).flatten() - 1,
                        "-",
                        linewidth=1,
                        alpha=0.9,
                    )
            except Exception as e:
                st.warning(f"Could not render tracks: {e}")
        plt.colorbar(im, ax=ax)
        ax.set_title(f"Tracks (n = {n_tracks})")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # ── Denoised Y ──────────────────────────────
    with tabs[1]:
        fig, ax = plt.subplots(figsize=(pw, ph))
        im = ax.imshow(-denoised_y, aspect="auto", cmap="viridis", origin="lower")
        if len(det_frames) > 0:
            ax.scatter(det_positions, det_frames, color="red", s=10, label="Detections")
            ax.legend()
        plt.colorbar(im, ax=ax)
        ax.set_title("Denoised (Y)")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # ── Contrast C ──────────────────────────────
    with tabs[2]:
        fig, ax = plt.subplots(figsize=(pw, ph))
        im = ax.imshow(-contrast_c, aspect="auto", cmap="viridis", origin="lower")
        if len(det_frames) > 0:
            ax.scatter(
                det_positions_refined, det_frames, color="white", s=10, label="Refined"
            )
            ax.legend()
        plt.colorbar(im, ax=ax)
        ax.set_title("Contrast (C)")
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    # ── Raw ─────────────────────────────────────
    if raw_data is not None:
        with tabs[3]:
            fig, ax = plt.subplots(figsize=(pw, ph))
            im = ax.imshow(raw_data, aspect="auto", cmap="gray", origin="lower")
            plt.colorbar(im, ax=ax)
            ax.set_title("Raw (R)")
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    # ── Detection table ─────────────────────────
    if len(det_frames) > 0:
        with st.expander("Detection details"):
            st.dataframe(
                pd.DataFrame({
                    "Frame": det_frames + 1,
                    "Position": det_positions + 1,
                    "Position Refined": det_positions_refined + 1,
                    "Contrast": results["det_contrast"],
                    "SNR": results["det_snr"]
                    if results["det_snr"] is not None
                    else np.nan,
                }),
                use_container_width=True,
            )


# ─────────────────────────────────────────────
# Sidebar — algorithm config
# ─────────────────────────────────────────────


def render_config_sidebar() -> dict:
    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("💾 Save / Load config"):
        uploaded_cfg = st.file_uploader(
            "Load config JSON", type=["json"], key="cfg_upload"
        )
        if uploaded_cfg:
            try:
                loaded = json.load(uploaded_cfg)
                for k, v in loaded.items():
                    if k in st.session_state:
                        st.session_state[k] = v
                st.success("Config loaded.")
            except Exception as e:
                st.error(f"Could not load config: {e}")

    config: dict[str, Any] = {}

    with st.sidebar.expander("Preprocessing", expanded=True):
        config["Kt"] = st.number_input(
            "Kt", value=DEFAULT_CONFIG["Kt"], step=1.0, key="Kt"
        )

    with st.sidebar.expander("Denoising"):
        config["spaceFilter"] = st.selectbox(
            "Space filter",
            ["jinc", "gaussian", "laplacean_of_gaussian", "none"],
            index=["jinc", "gaussian", "laplacean_of_gaussian", "none"].index(
                DEFAULT_CONFIG["spaceFilter"]
            ),
            key="spaceFilter",
        )
        config["sigma_x"] = st.number_input(
            "Sigma X", value=DEFAULT_CONFIG["sigma_x"], step=0.1, key="sigma_x"
        )
        config["timeFilter"] = st.selectbox(
            "Time filter",
            ["imgaussfilt", "none"],
            index=["imgaussfilt", "none"].index(DEFAULT_CONFIG["timeFilter"]),
            key="timeFilter",
        )
        config["sigma_t"] = st.number_input(
            "Sigma T", value=DEFAULT_CONFIG["sigma_t"], step=0.1, key="sigma_t"
        )
        config["nonLinearFilter"] = st.selectbox(
            "Non-linear filter",
            ["none", "nlm"],
            index=["none", "nlm"].index(DEFAULT_CONFIG["nonLinearFilter"]),
            key="nonLinearFilter",
        )

    with st.sidebar.expander("Detection"):
        config["pfa"] = st.number_input(
            "pfa", value=DEFAULT_CONFIG["pfa"], format="%.e", key="pfa"
        )
        config["localMinRange"] = st.number_input(
            "Local min range",
            value=DEFAULT_CONFIG["localMinRange"],
            step=1,
            key="localMinRange",
        )

    with st.sidebar.expander("Feature extraction"):
        config["positionRefinementMethod"] = st.selectbox(
            "Refinement method",
            ["centroid", "parabolic", "gaussian"],
            index=["centroid", "parabolic", "gaussian"].index(
                DEFAULT_CONFIG["positionRefinementMethod"]
            ),
            key="positionRefinementMethod",
        )
        config["fittingRadius"] = st.number_input(
            "Fitting radius",
            value=DEFAULT_CONFIG["fittingRadius"],
            step=1,
            key="fittingRadius",
        )

    with st.sidebar.expander("Linking / Tracking"):
        config["cut_off_distance"] = st.number_input(
            "Cut-off distance",
            value=DEFAULT_CONFIG["cut_off_distance"],
            step=1.0,
            key="cut_off_distance",
        )
        config["unmatched_penalty_distance"] = st.number_input(
            "Unmatched penalty",
            value=DEFAULT_CONFIG["unmatched_penalty_distance"],
            step=1.0,
            key="unmatched_penalty_distance",
        )
        config["flowEstimate"] = st.number_input(
            "Flow estimate",
            value=DEFAULT_CONFIG["flowEstimate"],
            step=0.1,
            key="flowEstimate",
        )
        config["minTrackLength"] = st.number_input(
            "Min track length",
            value=DEFAULT_CONFIG["minTrackLength"],
            step=1.0,
            key="minTrackLength",
        )
        st.caption("Gap closing")
        config["maxPositiveGab"] = st.number_input(
            "Max positive gap",
            value=DEFAULT_CONFIG["maxPositiveGab"],
            step=1.0,
            key="maxPositiveGab",
        )
        config["maxNegativeGab"] = st.number_input(
            "Max negative gap",
            value=DEFAULT_CONFIG["maxNegativeGab"],
            step=1.0,
            key="maxNegativeGab",
        )
        config["gab_closing_cut_off_distance"] = st.number_input(
            "Gap closing dist",
            value=DEFAULT_CONFIG["gab_closing_cut_off_distance"],
            step=1.0,
            key="gab_closing_cut_off_distance",
        )
        config["gab_closing_penalty_distance"] = st.number_input(
            "Gap closing penalty",
            value=DEFAULT_CONFIG["gab_closing_penalty_distance"],
            step=1.0,
            key="gab_closing_penalty_distance",
        )

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(config, indent=2),
        file_name="config.json",
        mime="application/json",
        use_container_width=True,
    )

    return config


# ─────────────────────────────────────────────
# Page: Submit
# ─────────────────────────────────────────────


def page_submit(config: dict) -> None:
    st.header("Submit Analysis")

    uploaded_files = st.file_uploader(
        "Upload .tiff files",
        type=["tif", "tiff"],
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
        st.info("Upload one or more .tiff files to begin.")
        return

    col_submit, col_wait = st.columns(2)
    with col_submit:
        submit = st.button(
            "Submit job",
            type="primary",
            disabled=(slots_free == 0),
            use_container_width=True,
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

    # ── Active wait ──────────────────────────────
    active_job_id = st.session_state.get("last_job_id")
    if active_job_id and st.session_state.get("waiting"):
        status_placeholder = st.empty()
        result_placeholder = st.empty()

        status = read_status(active_job_id)
        if status["status"] == "processing":
            status_placeholder.info(
                f"⏳ Running… (job `{active_job_id}`). Checking every {POLL_INTERVAL_S}s."
            )
            time.sleep(POLL_INTERVAL_S)
            st.rerun()
        else:
            st.session_state["waiting"] = False
            status_placeholder.empty()
            if status["status"] == "completed":
                result_placeholder.success("✅ Analysis complete!")
                _show_job_results(active_job_id)
            else:
                result_placeholder.error(
                    f"❌ Job failed: {status.get('error', 'unknown error')}"
                )


# ─────────────────────────────────────────────
# Page: History
# ─────────────────────────────────────────────

STATUS_ICON = {
    "processing": "⏳",
    "completed": "✅",
    "failed": "❌",
    "unknown": "❓",
}


def page_history() -> None:
    st.header("Experiment History")

    col_refresh, col_auto = st.columns([1, 3])
    with col_refresh:
        if st.button("Refresh", use_container_width=True):
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
            }
            for j in jobs
        ]),
        use_container_width=True,
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
            _show_job_results(selected_id)
    else:
        st.caption("No completed jobs to display yet.")

    # ── Admin: force-free stuck jobs ─────────────
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


def _show_job_results(job_id: str) -> None:
    """Render all .mat results for a given job."""
    _, _, out = job_dirs(job_id)
    mat_files = sorted(out.glob("*.mat"))

    if not mat_files:
        st.warning("No result files found yet.")
        return

    if len(mat_files) == 1:
        _render_single_mat(mat_files[0], job_id)
    else:
        file_names = [f.name for f in mat_files]
        session_key = f"mat_sel_{job_id}"
        # Initialise to first file if not already set or stale
        if (
            session_key not in st.session_state
            or st.session_state[session_key] not in file_names
        ):
            st.session_state[session_key] = file_names[0]
        selected_name = st.selectbox(
            "Select file",
            file_names,
            index=file_names.index(st.session_state[session_key]),
            key=session_key,
        )
        _render_single_mat(out / selected_name, job_id)


def _render_single_mat(mat_path: Path, job_id: str) -> None:
    st.subheader(mat_path.stem)
    results = load_mat_results(mat_path)
    if results is None:
        return

    _, inp, _ = job_dirs(job_id)
    tiff_path = inp / (mat_path.stem + ".tiff")
    if not tiff_path.exists():
        tiff_path = inp / (mat_path.stem + ".tif")

    raw_data = None
    if tiff_path.exists():
        try:
            raw_data = tifffile.imread(str(tiff_path))
        except Exception:
            pass  # raw tab simply won't appear

    render_results(results, raw_data)

    st.download_button(
        f"Download {mat_path.name}",
        data=mat_path.read_bytes(),
        file_name=mat_path.name,
        mime="application/octet-stream",
        key=f"dl_{mat_path.name}_{job_id}",
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
        2. Upload one or more `.tiff` files in the **Submit** tab.
        3. Click **Submit job**. Files are written to disk immediately and the
           MATLAB container starts in the background — your browser does not need
           to stay open.
        4. Enable **Wait for result** if you prefer to watch progress on this page.
        5. Once complete, results appear in the **History** tab. All users share
           the same history.

        ### Worker slots

        There are **{MAX_WORKERS}** concurrent MATLAB worker slots. If both are busy,
        wait for one to finish or arrange submission order with colleagues.

        ### File retention

        Input and output files are stored under `{DATA_DIR}`. Ask your system
        administrator about the retention policy.
        """)


if __name__ == "__main__":
    main()

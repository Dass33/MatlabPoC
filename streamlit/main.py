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
from glob import glob
from pathlib import Path
from typing import Any

import docker
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io
import streamlit as st

# ─────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data/jobs"))
HOST_DATA_DIR = Path(os.environ.get("HOST_DATA_DIR", str(DATA_DIR)))
MATLAB_IMAGE = os.environ.get("MATLAB_IMAGE", "nsm-matlab:latest")
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "2"))
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "5"))

DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG: dict[str, Any] = {
    # Acquisition
    "Dt": 0.007,
    "Dx": 0.066,
    "flipIntensity": True,
    "flowEstimate": -3.4,
    # Preprocessing
    "kymographPreprocessing": {"darkCalibration": 8, "Wx": 15, "Wt": 50, "ws": 2.36},
    # Detection
    "Detection": {"peakSign": "negative", "pfa": 1e-5, "localOptimumRange": 6},
    # Linking
    "Linking": {
        "minTrackLength": 10,
        "cut_off_distance": 20,
        "unmatched_penalty_distance": 15,
        "maxNegativeGab": 2,
        "maxPositiveGab": 3,
        "gab_closing_cut_off_distance": 40,
        "gab_closing_penalty_distance": 30,
    },
    # Trajectory properties to compute (positionStart/positionEnd always added separately)
    "trajectoryProperties": [
        "positionRefined", "timeFrame", "iOCprofile", "N",
        "iOC", "STDiOC", "D", "velocity",
    ],
    # Post-processing
    "iOCcalibration": "on",
    "outlierFiltering": {
        "referenceProperty": "iOC",
        "filterProperties": ["STDiOC", "velocity", "N", "positionStart", "positionEnd"],
        "thresholdDirection": ["upper", "both", "lower", "upper", "lower"],
        "thresholdValue": ["3std", "3std", "3std", "3std", "3std"],
    },
    # Population analysis
    "populationAnalysis": {"Title": "robustMean", "properties": ["iOC", "D", "velocity"]},
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
    uploaded_file.seek(0)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f, length=8 * 1024 * 1024)


def launch_matlab_container(job_id: str) -> None:
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


def load_summary(output_dir: Path) -> dict | None:
    p = output_dir / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as e:
        st.error(f"Could not read summary.json: {e}")
        return None


def load_trajectories(output_dir: Path) -> dict | None:
    p = output_dir / "trajectories.mat"
    if not p.exists():
        return None
    try:
        mat = scipy.io.loadmat(str(p))
        return {
            "iOC":           mat["iOC"].flatten(),
            "D":             mat["D"].flatten(),
            "velocity":      mat["velocity"].flatten(),
            "N":             mat["N"].flatten(),
            "positionStart": mat["positionStart"].flatten(),
            "positionEnd":   mat["positionEnd"].flatten(),
            "sweepIdx":      mat["sweepIdx"].flatten().astype(int),
            "sweepLegends":  [str(s[0]) for s in mat["sweepLegends"].flatten()],
        }
    except Exception as e:
        st.error(f"Could not read trajectories.mat: {e}")
        return None


def list_kymographs(output_dir: Path) -> list[Path]:
    kymo_dir = output_dir / "kymographs"
    if not kymo_dir.exists():
        return []
    return sorted(kymo_dir.glob("*.png"))


# ─────────────────────────────────────────────
# Sidebar — algorithm config
# ─────────────────────────────────────────────


def render_config_sidebar() -> dict:
    st.sidebar.header("Algorithm Parameters")

    with st.sidebar.expander("Save / Load config"):
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

    cfg = DEFAULT_CONFIG

    # ── Acquisition ──────────────────────────────────────────────────────
    with st.sidebar.expander("Acquisition", expanded=True):
        Dt = st.number_input("Dt (frame duration, s)", value=cfg["Dt"],
                             format="%.4f", step=0.001, key="Dt")
        Dx = st.number_input("Dx (pixel size, μm)", value=cfg["Dx"],
                             format="%.4f", step=0.001, key="Dx")
        flipIntensity = st.checkbox("Flip intensity", value=cfg["flipIntensity"],
                                    key="flipIntensity")
        flowEstimate = st.number_input("Flow estimate (px/frame)",
                                       value=cfg["flowEstimate"],
                                       format="%.2f", step=0.1, key="flowEstimate")

    # ── Preprocessing ────────────────────────────────────────────────────
    with st.sidebar.expander("Preprocessing"):
        darkCalibration = st.number_input("Dark calibration",
                                          value=int(cfg["kymographPreprocessing"]["darkCalibration"]),
                                          step=1, key="darkCalibration")
        Wx_sweep_enabled = st.session_state.get("sweep_enabled", False)
        if Wx_sweep_enabled:
            Wx_str = st.text_input("Wx values (comma-separated, px)",
                                   value=str(cfg["kymographPreprocessing"]["Wx"]),
                                   key="Wx_sweep")
            Wt_str = st.text_input("Wt values (comma-separated, frames)",
                                   value=str(cfg["kymographPreprocessing"]["Wt"]),
                                   key="Wt_sweep")
            Wx = _parse_sweep_values(Wx_str)
            Wt = _parse_sweep_values(Wt_str)
            if len(Wx) > 1 or len(Wt) > 1:
                n_sweeps = len(Wx) * len(Wt)
                st.caption(f"{len(Wx)} × {len(Wt)} = {n_sweeps} sweep(s) will run.")
        else:
            Wx = st.number_input("Wx (spatial window, px)",
                                 value=float(cfg["kymographPreprocessing"]["Wx"]),
                                 step=1.0, key="Wx_single")
            Wt = st.number_input("Wt (temporal window, frames)",
                                 value=float(cfg["kymographPreprocessing"]["Wt"]),
                                 step=1.0, key="Wt_single")
        ws = st.number_input("ws (PSF width, px)",
                             value=cfg["kymographPreprocessing"]["ws"],
                             format="%.2f", step=0.01, key="ws")

    # ── Detection ────────────────────────────────────────────────────────
    with st.sidebar.expander("Detection"):
        peakSign = st.selectbox("Peak sign",
                                ["negative", "positive", "negative-positive"],
                                index=0, key="peakSign")
        pfa = st.number_input("pfa", value=cfg["Detection"]["pfa"],
                              format="%.e", key="pfa")
        localOptimumRange = st.number_input("Local optimum range",
                                            value=int(cfg["Detection"]["localOptimumRange"]),
                                            step=1, key="localOptimumRange")

    # ── Tracking ─────────────────────────────────────────────────────────
    with st.sidebar.expander("Tracking"):
        minTrackLength = st.number_input("Min track length",
                                         value=int(cfg["Linking"]["minTrackLength"]),
                                         step=1, key="minTrackLength")
        cut_off_distance = st.number_input("Cut-off distance",
                                           value=float(cfg["Linking"]["cut_off_distance"]),
                                           step=1.0, key="cut_off_distance")
        unmatched_penalty_distance = st.number_input("Unmatched penalty distance",
                                                     value=float(cfg["Linking"]["unmatched_penalty_distance"]),
                                                     step=1.0, key="unmatched_penalty_distance")
        maxNegativeGab = st.number_input("Max negative gap",
                                         value=int(cfg["Linking"]["maxNegativeGab"]),
                                         step=1, key="maxNegativeGab")
        maxPositiveGab = st.number_input("Max positive gap",
                                         value=int(cfg["Linking"]["maxPositiveGab"]),
                                         step=1, key="maxPositiveGab")
        gab_closing_cut_off_distance = st.number_input("Gap closing cut-off distance",
                                                       value=float(cfg["Linking"]["gab_closing_cut_off_distance"]),
                                                       step=1.0, key="gab_closing_cut_off_distance")
        gab_closing_penalty_distance = st.number_input("Gap closing penalty distance",
                                                       value=float(cfg["Linking"]["gab_closing_penalty_distance"]),
                                                       step=1.0, key="gab_closing_penalty_distance")

    # ── Post-processing ──────────────────────────────────────────────────
    with st.sidebar.expander("Post-processing"):
        ioc_cal_on = st.toggle("iOC calibration", value=(cfg["iOCcalibration"] == "on"),
                               key="iOCcalibration_toggle")
        iOCcalibration = "on" if ioc_cal_on else "off"
        st.caption("Outlier filtering properties and thresholds use defaults (upload config JSON for full control).")

    # ── Population analysis ──────────────────────────────────────────────
    with st.sidebar.expander("Population analysis"):
        pop_method = st.selectbox("Method", ["robustMean", "GMM"],
                                  index=0, key="pop_method")

    # ── Parameter sweep ──────────────────────────────────────────────────
    with st.sidebar.expander("Parameter sweep", expanded=False):
        sweep_enabled = st.checkbox("Enable sweep (Wx × Wt)", value=False,
                                    key="sweep_enabled")

    st.sidebar.download_button(
        "Export current config",
        data=json.dumps(_build_config(
            Dt, Dx, flipIntensity, flowEstimate,
            darkCalibration, Wx, Wt, ws,
            peakSign, pfa, localOptimumRange,
            minTrackLength, cut_off_distance, unmatched_penalty_distance,
            maxNegativeGab, maxPositiveGab,
            gab_closing_cut_off_distance, gab_closing_penalty_distance,
            iOCcalibration, pop_method,
        ), indent=2),
        file_name="config.json",
        mime="application/json",
        use_container_width=True,
    )

    return _build_config(
        Dt, Dx, flipIntensity, flowEstimate,
        darkCalibration, Wx, Wt, ws,
        peakSign, pfa, localOptimumRange,
        minTrackLength, cut_off_distance, unmatched_penalty_distance,
        maxNegativeGab, maxPositiveGab,
        gab_closing_cut_off_distance, gab_closing_penalty_distance,
        iOCcalibration, pop_method,
    )


def _parse_sweep_values(s: str) -> list[float]:
    try:
        return [float(v.strip()) for v in s.split(",") if v.strip()]
    except ValueError:
        return [15.0]


def _build_config(
    Dt, Dx, flipIntensity, flowEstimate,
    darkCalibration, Wx, Wt, ws,
    peakSign, pfa, localOptimumRange,
    minTrackLength, cut_off_distance, unmatched_penalty_distance,
    maxNegativeGab, maxPositiveGab,
    gab_closing_cut_off_distance, gab_closing_penalty_distance,
    iOCcalibration, pop_method,
) -> dict:
    cfg = DEFAULT_CONFIG.copy()
    cfg["Dt"] = Dt
    cfg["Dx"] = Dx
    cfg["flipIntensity"] = flipIntensity
    cfg["flowEstimate"] = flowEstimate
    cfg["kymographPreprocessing"] = {
        "darkCalibration": int(darkCalibration),
        "Wx": Wx if isinstance(Wx, list) else float(Wx),
        "Wt": Wt if isinstance(Wt, list) else float(Wt),
        "ws": float(ws),
    }
    cfg["Detection"] = {
        "peakSign": peakSign,
        "pfa": float(pfa),
        "localOptimumRange": int(localOptimumRange),
    }
    cfg["Linking"] = {
        "minTrackLength": int(minTrackLength),
        "cut_off_distance": float(cut_off_distance),
        "unmatched_penalty_distance": float(unmatched_penalty_distance),
        "maxNegativeGab": int(maxNegativeGab),
        "maxPositiveGab": int(maxPositiveGab),
        "gab_closing_cut_off_distance": float(gab_closing_cut_off_distance),
        "gab_closing_penalty_distance": float(gab_closing_penalty_distance),
    }
    cfg["iOCcalibration"] = iOCcalibration
    cfg["populationAnalysis"]["Title"] = pop_method
    return cfg


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
        st.info("Upload one or more .tiff files and their paired .txt metadata files to begin.")
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
                _show_job_results(active_job_id)
            else:
                result_placeholder.error(
                    f"Job failed: {status.get('error', 'unknown error')}"
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
    _, _, out = job_dirs(job_id)

    summary = load_summary(out)
    traj = load_trajectories(out)
    kymographs = list_kymographs(out)

    if summary is None and traj is None and not kymographs:
        st.warning("No result files found yet.")
        return

    tab_kymo, tab_traj, tab_pop, tab_table = st.tabs(
        ["Kymographs", "Trajectories", "Population", "Summary"]
    )

    with tab_kymo:
        _render_kymographs(kymographs, job_id)

    with tab_traj:
        _render_trajectories(traj, job_id)

    with tab_pop:
        _render_population(summary)

    with tab_table:
        _render_summary_table(summary)


# ─────────────────────────────────────────────
# Result tabs
# ─────────────────────────────────────────────


def _render_kymographs(kymographs: list[Path], job_id: str) -> None:
    if not kymographs:
        st.info("No kymograph images found.")
        return

    names = [p.name for p in kymographs]
    sel = st.selectbox("Select kymograph", names, key=f"kymo_sel_{job_id}")
    kymo_path = next(p for p in kymographs if p.name == sel)
    st.image(str(kymo_path), use_container_width=True)


def _render_trajectories(traj: dict | None, job_id: str) -> None:
    if traj is None:
        st.info("trajectories.mat not found.")
        return

    sweep_legends = traj["sweepLegends"]
    sweep_idx = traj["sweepIdx"]

    sweep_options = list(dict.fromkeys(sweep_legends))  # preserve order, deduplicate
    if len(sweep_options) > 1:
        sel_sweep = st.selectbox("Select sweep", sweep_options, key=f"traj_sweep_sel_{job_id}")
        mask = sweep_idx == (sweep_options.index(sel_sweep) + 1)
    else:
        mask = np.ones(len(sweep_idx), dtype=bool)

    ioc = traj["iOC"][mask]
    D   = traj["D"][mask]
    vel = traj["velocity"][mask]
    N   = traj["N"][mask]

    if len(ioc) == 0:
        st.info("No trajectories in this sweep.")
        return

    st.metric("Trajectories", int(mask.sum()))

    # Scatter: iOC vs trajectory index, coloured by D
    fig, ax = plt.subplots(figsize=(10, 4))
    sc = ax.scatter(np.arange(len(ioc)), ioc, c=D, cmap="viridis", s=10)
    plt.colorbar(sc, ax=ax, label="D")
    ax.set_xlabel("Trajectory index")
    ax.set_ylabel("iOC")
    ax.set_title("iOC per trajectory (coloured by D)")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    # Histograms 2×2
    fig, axes = plt.subplots(2, 2, figsize=(10, 6))
    for ax, data, label in zip(
        axes.flat,
        [ioc, D, vel, N],
        ["iOC", "D", "velocity", "N"],
    ):
        ax.hist(data[np.isfinite(data)], bins=30)
        ax.set_xlabel(label)
        ax.set_ylabel("Count")
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def _render_population(summary: dict | None) -> None:
    if summary is None:
        st.info("summary.json not found.")
        return

    sweeps = summary.get("sweeps", [])
    if not sweeps:
        st.info("No sweep data in summary.")
        return

    props = list(sweeps[0].get("MEAN", {}).keys())

    for prop in props:
        st.subheader(prop)
        cols = st.columns(len(sweeps))
        for col, sweep in zip(cols, sweeps):
            with col:
                mean_val = sweep.get("MEAN", {}).get(prop, float("nan"))
                fwhm_val = sweep.get("FWHM", {}).get(prop, float("nan"))
                res_val  = sweep.get("RESOLUTION", {}).get(prop, float("nan"))
                legend   = sweep.get("legend", "")
                st.metric(f"{legend} MEAN", f"{mean_val:.4g}")
                st.metric("FWHM", f"{fwhm_val:.4g}")
                st.metric("RESOLUTION", f"{res_val:.4g}")

    # Bar chart of MEAN values across sweeps for each property
    if len(sweeps) > 1:
        st.subheader("Sweep comparison")
        for prop in props:
            means = [s.get("MEAN", {}).get(prop, float("nan")) for s in sweeps]
            fwhms = [s.get("FWHM", {}).get(prop, float("nan")) for s in sweeps]
            legends = [s.get("legend", f"Sweep {i+1}") for i, s in enumerate(sweeps)]

            fig, ax = plt.subplots(figsize=(max(6, len(sweeps) * 1.5), 4))
            x = np.arange(len(sweeps))
            ax.bar(x, means, yerr=fwhms, capsize=4, width=0.6)
            ax.set_xticks(x)
            ax.set_xticklabels(legends, rotation=20, ha="right")
            ax.set_ylabel(prop)
            ax.set_title(f"{prop} MEAN ± FWHM")
            fig.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)


def _render_summary_table(summary: dict | None) -> None:
    if summary is None:
        st.info("summary.json not found.")
        return

    sweeps = summary.get("sweeps", [])
    if not sweeps:
        st.info("No sweep data in summary.")
        return

    props = list(sweeps[0].get("MEAN", {}).keys())

    rows = []
    for s in sweeps:
        row = {"Sweep": s.get("legend", ""), "N trajectories": s.get("nTrajectories", 0)}
        for prop in props:
            row[f"{prop} MEAN"] = s.get("MEAN", {}).get(prop, float("nan"))
            row[f"{prop} FWHM"] = s.get("FWHM", {}).get(prop, float("nan"))
            row[f"{prop} RESOLUTION"] = s.get("RESOLUTION", {}).get(prop, float("nan"))
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


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
        wait for one to finish or arrange submission order with colleagues.

        ### File retention

        Input and output files are stored under `{DATA_DIR}`. Ask your system
        administrator about the retention policy.
        """)


if __name__ == "__main__":
    main()

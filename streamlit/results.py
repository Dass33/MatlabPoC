from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy.io
from job_manager import job_dirs

import streamlit as st


def load_summary(output_dir: Path) -> dict | None:
    p = output_dir / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        st.error(f"Could not read summary.json: {e}")
        return None


def load_trajectories(output_dir: Path) -> dict | None:
    p = output_dir / "trajectories.mat"
    if not p.exists():
        return None
    try:
        mat = scipy.io.loadmat(str(p))
        return {
            "iOC": mat["iOC"].flatten(),
            "D": mat["D"].flatten(),
            "velocity": mat["velocity"].flatten(),
            "N": mat["N"].flatten(),
            "positionStart": mat["positionStart"].flatten(),
            "positionEnd": mat["positionEnd"].flatten(),
            "sweepIdx": mat["sweepIdx"].flatten().astype(int),
            "sweepLegends": [str(s[0]) for s in mat["sweepLegends"].flatten()],
        }
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not read trajectories.mat: {e}")
        return None


def list_kymographs(output_dir: Path) -> list[Path]:
    kymo_dir = output_dir / "kymographs"
    if not kymo_dir.exists():
        return []
    return sorted(kymo_dir.glob("*.png"))


def show_job_results(job_id: str, key_suffix: str = "") -> None:
    _, _, out = job_dirs(job_id)

    summary = load_summary(out)
    traj = load_trajectories(out)
    kymographs = list_kymographs(out)

    if summary is None and traj is None and not kymographs:
        st.warning("No result files found yet.")
        return

    tab_kymo, tab_traj, tab_pop, tab_table = st.tabs([
        "Kymographs",
        "Trajectories",
        "Population",
        "Summary",
    ])

    with tab_kymo:
        render_kymographs(kymographs, job_id, key_suffix)

    with tab_traj:
        _render_trajectories(traj, job_id, key_suffix)

    with tab_pop:
        render_population(summary)

    with tab_table:
        render_summary_table(summary)


def render_kymographs(
    kymographs: list[Path], job_id: str, key_suffix: str = ""
) -> None:
    if not kymographs:
        st.info("No kymograph images found.")
        return

    names = [p.name for p in kymographs]
    sel = st.selectbox("Select kymograph", names, key=f"kymo_sel_{job_id}_{key_suffix}")
    kymo_path = next(p for p in kymographs if p.name == sel)
    st.image(str(kymo_path), width="stretch")


def _render_trajectories(traj: dict | None, job_id: str, key_suffix: str = "") -> None:
    if traj is None:
        st.info("trajectories.mat not found.")
        return

    sweep_legends = traj["sweepLegends"]
    sweep_idx = traj["sweepIdx"]

    sweep_options = list(dict.fromkeys(sweep_legends))  # preserve order, deduplicate
    if len(sweep_options) > 1:
        sel_sweep = st.selectbox(
            "Select sweep", sweep_options, key=f"traj_sweep_sel_{job_id}_{key_suffix}"
        )
        mask = sweep_idx == (sweep_options.index(sel_sweep) + 1)
    else:
        mask = np.ones(len(sweep_idx), dtype=bool)

    ioc = traj["iOC"][mask]
    D = traj["D"][mask]
    vel = traj["velocity"][mask]
    N = traj["N"][mask]

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
    st.pyplot(fig, width="stretch")
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
    st.pyplot(fig, width="stretch")
    plt.close(fig)


def render_population(summary: dict | None) -> None:
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
                std_val = sweep.get("STD", {}).get(prop, float("nan"))
                fwhm_val = sweep.get("FWHM", {}).get(prop, float("nan"))
                res_val = sweep.get("RESOLUTION", {}).get(prop, float("nan"))
                legend = sweep.get("legend", "")
                st.metric(f"{legend} MEAN", f"{mean_val:.4g}")
                st.metric("STD", f"{std_val:.4g}")
                st.metric("FWHM", f"{fwhm_val:.4g}")
                st.metric("RESOLUTION", f"{res_val:.4g}")

    # Bar chart of MEAN values across sweeps for each property
    if len(sweeps) > 1:
        st.subheader("Sweep comparison")
        for prop in props:
            means = [s.get("MEAN", {}).get(prop, float("nan")) for s in sweeps]
            fwhms = [s.get("FWHM", {}).get(prop, float("nan")) for s in sweeps]
            legends = [s.get("legend", f"Sweep {i + 1}") for i, s in enumerate(sweeps)]

            fig, ax = plt.subplots(figsize=(max(6, len(sweeps) * 1.5), 4))
            x = np.arange(len(sweeps))
            ax.bar(x, means, yerr=fwhms, capsize=4, width=0.6)
            ax.set_xticks(x)
            ax.set_xticklabels(legends, rotation=20, ha="right")
            ax.set_ylabel(prop)
            ax.set_title(f"{prop} MEAN ± FWHM")
            fig.tight_layout()
            st.pyplot(fig, width="stretch")
            plt.close(fig)


def render_summary_table(summary: dict | None) -> None:
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
        row = {
            "Sweep": s.get("legend", ""),
            "N trajectories": s.get("nTrajectories", 0),
        }
        for prop in props:
            row[f"{prop} MEAN"] = s.get("MEAN", {}).get(prop, float("nan"))
            row[f"{prop} STD"] = s.get("STD", {}).get(prop, float("nan"))
            row[f"{prop} FWHM"] = s.get("FWHM", {}).get(prop, float("nan"))
            row[f"{prop} RESOLUTION"] = s.get("RESOLUTION", {}).get(prop, float("nan"))
        rows.append(row)

    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

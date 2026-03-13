from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from job_manager import job_dirs

import streamlit as st


def show_job_results(job_id: str, key_suffix: str = "") -> None:
    _, _, out = job_dirs(job_id)

    summary = load_summary(out)
    kymographs = list_kymographs(out)

    if summary is None and not kymographs:
        st.warning("No result files found yet.")
        return

    tab_kymo, tab_table = st.tabs([
        "Kymographs",
        "Summary",
    ])

    with tab_kymo:
        render_kymographs(kymographs, job_id, key_suffix)

    with tab_table:
        render_summary_table(summary)


def load_summary(output_dir: Path) -> dict | None:
    p = output_dir / "summary.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError) as e:
        st.error(f"Could not read summary.json: {e}")
        return None


def list_kymographs(output_dir: Path) -> list[Path]:
    kymo_dir = output_dir / "kymographs"
    if not kymo_dir.exists():
        return []
    return sorted(kymo_dir.glob("*.png"))


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

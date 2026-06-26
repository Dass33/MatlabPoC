from __future__ import annotations

from pathlib import Path

import streamlit as st

from env import job_dirs


def page_kymograph_analysis(job_id: str | None) -> None:
    """Kymograph Analysis tab — browse rendered kymograph images from a completed job."""
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    _, _, out = job_dirs(job_id)

    def list_kymographs(output_dir: Path) -> list[Path]:
        kymo_dir = output_dir / "kymographs"
        if not kymo_dir.exists():
            return []
        return sorted(kymo_dir.glob("*.png"))

    kymographs = list_kymographs(out)

    if not kymographs:
        st.info("No kymograph images found, analysis may still be running.")
        return

    names = [p.name for p in kymographs]
    sel = st.selectbox("Select kymograph", names, key=f"kymo_sel_{job_id}")
    path = next(p for p in kymographs if p.name == sel)
    st.image(str(path), width="stretch")

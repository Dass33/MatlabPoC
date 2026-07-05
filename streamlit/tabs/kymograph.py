from __future__ import annotations

from pathlib import Path

import streamlit as st

from connectors.storage import read_status
from env import job_dirs


def page_kymograph_analysis(job_id: str | None) -> None:
    if job_id is None:
        st.info("Select a completed experiment from the dropdown above.")
        return

    _, inp, out = job_dirs(job_id)
    status = read_status(job_id)

    if status["status"] == "processing":
        _live_view(job_id, inp, out)
    elif status["status"] == "failed":
        st.error(f"Job failed: {status.get('error', 'unknown error')}")
    else:
        _static_view(job_id, out)


@st.fragment(run_every=3)
def _live_view(job_id: str, inp: Path, out: Path) -> None:
    status = read_status(job_id)

    if status["status"] != "processing":
        st.rerun()
        return

    kymographs = _list_kymographs(out)
    total = _count_tiffs(inp)
    done = len(kymographs)

    if total:
        st.info(f"Running... {done}/{total} files done")
        st.progress(done / total)
    else:
        st.info("Running...")

    if kymographs:
        _render_picker(job_id, kymographs)


def _static_view(job_id: str, out: Path) -> None:
    kymographs = _list_kymographs(out)
    if not kymographs:
        st.info("No kymograph images found.")
        return
    _render_picker(job_id, kymographs)


def _render_picker(job_id: str, kymographs: list[Path]) -> None:
    names = [p.name for p in kymographs]
    sel = st.selectbox("Select kymograph", names, key=f"kymo_sel_{job_id}")
    path = next(p for p in kymographs if p.name == sel)
    st.image(str(path), width="stretch")


def _list_kymographs(out: Path) -> list[Path]:
    kymo_dir = out / "kymographs"
    if not kymo_dir.exists():
        return []
    return sorted(kymo_dir.glob("*.png"))


def _count_tiffs(inp: Path) -> int:
    if not inp.exists():
        return 0
    return sum(1 for _ in inp.glob("*.tiff")) + sum(1 for _ in inp.glob("*.tif"))

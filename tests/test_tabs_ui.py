"""UI regression tests for the deep tabs with the MATLAB bridge mocked out.

Like test_app_ui.py these drive the real Streamlit script via AppTest, but they
seed completed jobs on disk and stub connectors.algorithms, so the Kymograph,
Post-processing, Population, and Overview flows run in seconds without the MCR.
test_deep_tabs.py covers the same postprocessing/population flows against real
MATLAB; keep the two in sync when the tab wiring changes.
"""

from __future__ import annotations

import json

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

from connectors import algorithms, storage
from sample_data import sample_collection, write_collection_mat

APP = "streamlit/main.py"

_N_TRAJ = 10


@pytest.fixture(autouse=True)
def _clear_streamlit_caches():
    """st.cache_data persists per-process; AppTest runs in-process, so cached
    outlier masks / loaded collections would leak between tests."""
    import streamlit as st

    st.cache_data.clear()


@pytest.fixture
def fake_matlab(monkeypatch):
    """Stub the three MCR entry points the tabs call, with plausible shapes."""

    def find_outliers_json(collection_json: str, setting_json: str) -> np.ndarray:
        n = len(json.loads(collection_json)["iOC"])
        return np.ones(n, dtype=bool)

    def run_postprocessing(collection, matlab_setting, keep_mask, force_keep,
                           calibration_on=True):
        mask = keep_mask.copy()
        mask[0] = False  # pretend the filter drops trajectory 0
        return {"notOutlier": mask, "calibration": None}

    def run_population_analysis(collection, setting):
        return {
            p: {"MEAN": 1.5e-6, "STD": 2e-7, "FWHM": 3e-7, "RESOLUTION": 0.1,
                "_hist_centers": [0.0, 1.0], "_hist_counts": [1, 2]}
            for p in setting["properties"]
        }

    monkeypatch.setattr(algorithms, "find_outliers_json", find_outliers_json)
    monkeypatch.setattr(algorithms, "run_postprocessing", run_postprocessing)
    monkeypatch.setattr(algorithms, "run_population_analysis", run_population_analysis)


def _seed_job(make_upload, status="completed", name="job", error=None):
    job_id = storage.create_job([make_upload("a.tif", b"x")], {"Dt": 0.1}, name=name)
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": status, "error": error}))
    return job_id


def _seed_collection(job_id, n=_N_TRAJ):
    _, _, out = storage.job_dirs(job_id)
    write_collection_mat(out, sample_collection(n=n))


def _seed_postprocessed(job_id, n=_N_TRAJ):
    _, _, out = storage.job_dirs(job_id)
    data = {
        "collection": algorithms._prep_collection(sample_collection(n=n)),
        "calibration": None,
        "n_kept": n,
        "n_total": n,
    }
    (out / "collection_postprocessed.json").write_text(json.dumps(data))


def _seed_population(job_id, props=("iOC", "D", "velocity")):
    _, _, out = storage.job_dirs(job_id)
    (out / "population.json").write_text(json.dumps({
        "method": "robustMean",
        "properties": list(props),
        "n_trajectories": _N_TRAJ,
        "results": {p: {"MEAN": 1e-6, "STD": 1e-7} for p in props},
    }))


def _run_app(job_id=None):
    at = AppTest.from_file(APP, default_timeout=60)
    if job_id:
        at.session_state["active_experiment"] = job_id
    return at.run()


# --- Kymograph tab ---


def test_kymograph_lists_pngs_for_completed_job(make_upload, tiny_png):
    job_id = _seed_job(make_upload)
    _, _, out = storage.job_dirs(job_id)
    (out / "kymographs").mkdir()
    (out / "kymographs" / "b.png").write_bytes(tiny_png)
    (out / "kymographs" / "a.png").write_bytes(tiny_png)

    at = _run_app(job_id)
    assert not at.exception
    assert at.selectbox(key=f"kymo_sel_{job_id}").options == ["a.png", "b.png"]


def test_kymograph_completed_without_images_shows_info(make_upload):
    job_id = _seed_job(make_upload)
    at = _run_app(job_id)
    assert not at.exception
    assert any("No kymograph images found" in i.value for i in at.info)


def test_kymograph_failed_job_shows_error(make_upload):
    # no completed jobs -> no selector; the failed job stays active via session_state
    job_id = _seed_job(make_upload, status="failed", error="MATLAB exploded")
    at = _run_app(job_id)
    assert not at.exception
    assert any("MATLAB exploded" in e.value for e in at.error)


# --- Post-processing tab ---


def test_postprocessing_renders_thresholds_and_kept_count(make_upload, fake_matlab):
    job_id = _seed_job(make_upload)
    _seed_collection(job_id)

    at = _run_app(job_id)
    assert not at.exception
    assert at.checkbox(key=f"pp_en_{job_id}_iOC").value is True
    assert any(f"{_N_TRAJ}/{_N_TRAJ} kept" in c.value for c in at.caption)


def test_postprocessing_accept_saves_and_clears_dirty(make_upload, fake_matlab):
    job_id = _seed_job(make_upload)
    _seed_collection(job_id)

    at = _run_app(job_id)
    at.button(key=f"pp_apply_{job_id}").click().run()
    assert not at.exception

    _, _, out = storage.job_dirs(job_id)
    data = json.loads((out / "collection_postprocessed.json").read_text())
    assert data["n_total"] == _N_TRAJ
    assert data["n_kept"] == _N_TRAJ - 1  # fake filter drops trajectory 0
    assert any(f"Saved {_N_TRAJ - 1} / {_N_TRAJ}" in s.value for s in at.success)
    # curation persisted for the next session
    assert (out / "postprocessing_state.json").exists()
    # dirty flag cleared -> no recalibrate hint
    assert not any("recalibrate" in c.value for c in at.caption)


def test_postprocessing_threshold_change_marks_dirty_again(make_upload, fake_matlab):
    job_id = _seed_job(make_upload)
    _seed_collection(job_id)

    at = _run_app(job_id)
    at.button(key=f"pp_apply_{job_id}").click().run()
    assert not any("recalibrate" in c.value for c in at.caption)

    at.checkbox(key=f"pp_en_{job_id}_iOC").uncheck().run()
    assert not at.exception
    assert any("recalibrate" in c.value for c in at.caption)


def test_postprocessing_missing_collection_warns(make_upload):
    job_id = _seed_job(make_upload)
    at = _run_app(job_id)
    assert not at.exception
    assert any("collection.mat not found" in w.value for w in at.warning)


# --- Population tab ---


def test_population_warns_without_postprocessed_collection(make_upload, fake_matlab):
    job_id = _seed_job(make_upload)
    _seed_collection(job_id)
    at = _run_app(job_id)
    assert not at.exception
    assert any("Run postprocessing first" in w.value for w in at.warning)


def test_population_run_persists_results_and_renders_table(make_upload, fake_matlab):
    job_id = _seed_job(make_upload)
    _seed_collection(job_id)
    _seed_postprocessed(job_id)

    at = _run_app(job_id)
    at.button(key=f"pop_run_{job_id}").click().run()
    assert not at.exception

    _, _, out = storage.job_dirs(job_id)
    saved = json.loads((out / "population.json").read_text())
    assert saved["method"] == "robustMean"
    assert saved["n_trajectories"] == _N_TRAJ
    assert saved["results"]["iOC"]["MEAN"] == pytest.approx(1.5e-6)
    # private histogram keys are stripped before persisting
    assert "_hist_centers" not in saved["results"]["iOC"]
    # stats table rendered
    assert any("MEAN" in d.value.columns for d in at.dataframe)


def test_population_compare_section_with_two_jobs(make_upload, fake_matlab):
    jobs = [_seed_job(make_upload, name=n) for n in ("one", "two")]
    for j in jobs:
        _seed_collection(j)
        _seed_postprocessed(j)
        _seed_population(j)

    at = _run_app(jobs[0])
    at.multiselect(key="compare_jobs").set_value(jobs).run()
    assert not at.exception
    # common properties found across both jobs and preselected
    assert at.multiselect(key="compare_props").value


# --- Overview tab ---


def test_overview_lists_jobs_with_status_and_failure_detail(make_upload):
    _seed_job(make_upload, name="good")
    _seed_job(make_upload, status="failed", name="broken", error="boom")

    at = _run_app()
    assert not at.exception
    df = next(d.value for d in at.dataframe if "Name" in d.value.columns)
    assert set(df["Name"]) == {"good", "broken"}
    assert any("failed" in s for s in df["Status"])
    assert any("boom" in e.value for e in at.error)


def test_overview_mark_stuck_job_as_failed(make_upload):
    job_id = _seed_job(make_upload, status="processing", name="stuck")

    at = _run_app()
    at.button(key="admin_force").click().run()
    assert not at.exception
    assert storage.read_status(job_id)["status"] == "failed"

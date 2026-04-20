"""
Layer 2 integration tests — require Docker + matlab-algorithm:latest.
Run with: pytest --run-integration
"""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))

from conftest import MockFile, SYNTH_TIFF_DIR, FIXTURE_STEM, _load_job_manager, _poll_until_done, _tiff_pair


# ── Pipeline completion ───────────────────────────────────────────────────────


@pytest.mark.integration
def test_pipeline_completes(completed_job):
    assert completed_job["status"]["status"] == "completed"


@pytest.mark.integration
def test_pipeline_output_structure(completed_job):
    jm = completed_job["jm"]
    _, _, out = jm.job_dirs(completed_job["job_id"])

    assert (out / "status.json").exists()
    assert (out / "Setting.json").exists()
    assert (out / "collection" / "collection.mat").exists()

    kymographs = list((out / "kymographs").glob("*.png"))
    assert len(kymographs) >= 1, "Expected at least one kymograph PNG"


@pytest.mark.integration
def test_pipeline_status_json_valid(completed_job):
    jm = completed_job["jm"]
    _, _, out = jm.job_dirs(completed_job["job_id"])
    status = json.loads((out / "status.json").read_text())
    assert status["status"] == "completed"
    assert "error" in status


@pytest.mark.integration
def test_pipeline_collection_has_trajectories(completed_job):
    import scipy.io

    jm = completed_job["jm"]
    _, _, out = jm.job_dirs(completed_job["job_id"])
    m = scipy.io.loadmat(str(out / "collection" / "collection.mat"), squeeze_me=True)
    c = m["collection"]
    n_trajectories = len(c["iOC"].item())
    assert n_trajectories > 0, "Expected at least one detected trajectory"


# ── Export optional figures ───────────────────────────────────────────────────


@pytest.mark.integration
def test_pipeline_export_optional_figures(tmp_path_factory):
    from config import DEFAULT_CONFIG

    data_dir = tmp_path_factory.mktemp("jobs_optional")
    jm = _load_job_manager(data_dir)

    config_with = {**DEFAULT_CONFIG, "exportOptionalFigures": True}
    config_without = {**DEFAULT_CONFIG, "exportOptionalFigures": False}

    job_with = jm.submit_job(_tiff_pair(FIXTURE_STEM), config_with)
    job_without = jm.submit_job(_tiff_pair(FIXTURE_STEM), config_without)

    status_with = _poll_until_done(jm, job_with)
    status_without = _poll_until_done(jm, job_without)

    assert status_with["status"] == "completed"
    assert status_without["status"] == "completed"

    _, _, out_with = jm.job_dirs(job_with)
    _, _, out_without = jm.job_dirs(job_without)

    files_with = set(p.name for p in out_with.rglob("*") if p.is_file())
    files_without = set(p.name for p in out_without.rglob("*") if p.is_file())

    assert files_with != files_without, (
        "exportOptionalFigures=True should produce additional output files"
    )
    assert len(files_with) > len(files_without), (
        f"Optional figures job has {len(files_with)} files, non-optional has {len(files_without)}"
    )


# ── Invalid config ────────────────────────────────────────────────────────────


@pytest.mark.integration
def test_pipeline_missing_required_config_field_fails(tmp_path_factory):
    from config import DEFAULT_CONFIG

    data_dir = tmp_path_factory.mktemp("jobs_invalid")
    jm = _load_job_manager(data_dir)

    bad_config = copy.deepcopy(DEFAULT_CONFIG)
    del bad_config["Dt"]

    job_id = jm.submit_job(_tiff_pair(FIXTURE_STEM), bad_config)
    status = _poll_until_done(jm, job_id)

    assert status["status"] == "failed"
    assert status.get("error") not in (None, "", [])

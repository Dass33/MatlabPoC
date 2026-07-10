"""Tests for core.report.build_report and the Overview results zip.

_zip_results swallows report/export exceptions and just logs them, so a broken
build_report would silently ship zips without report.html — the namelist
assertion here is what catches that.
"""

from __future__ import annotations

import io
import json
import zipfile

from connectors import algorithms, storage
from core.report import build_report
from sample_data import sample_collection, write_collection_mat
from tabs.overview import _zip_results


def _seed_full_job(make_upload, tiny_png):
    """A completed job with every artifact the report/zip can pick up."""
    job_id = storage.create_job(
        [make_upload("a.tif", b"x"), make_upload("a.txt", b"m")],
        {"Dt": 0.05, "tracker": "simple"},
        name="full run",
    )
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))
    (out / "kymographs").mkdir()
    (out / "kymographs" / "a.png").write_bytes(tiny_png)
    write_collection_mat(out, sample_collection(n=10))
    (out / "collection_postprocessed.json").write_text(json.dumps({
        "collection": algorithms._prep_collection(sample_collection(n=10)),
        "calibration": None,
        "n_kept": 9,
        "n_total": 10,
    }))
    (out / "population.json").write_text(json.dumps({
        "method": "robustMean",
        "properties": ["iOC", "D"],
        "n_trajectories": 9,
        "results": {
            "iOC": {"MEAN": 1.5e-6, "STD": 2e-7, "FWHM": 3e-7, "RESOLUTION": 0.1},
            "D": {"MEAN": 1.0, "STD": 0.1},
        },
    }))
    return job_id


def test_build_report_includes_all_sections(make_upload, tiny_png):
    job_id = _seed_full_job(make_upload, tiny_png)
    html_report = build_report(job_id)

    assert "full run" in html_report  # header uses the job name
    assert "9 of 10 trajectories kept" in html_report
    assert "Population Statistics" in html_report
    assert "<td>1.5</td>" in html_report  # iOC MEAN scaled to µ
    assert "Dt" in html_report  # key params from config
    assert "data:image/png;base64" in html_report  # embedded kymograph/scatter


def test_build_report_survives_missing_artifacts(make_upload):
    job_id = storage.create_job([make_upload("a.tif", b"x")], {}, name="bare")
    html_report = build_report(job_id)
    assert "bare" in html_report
    assert "No kymographs available" in html_report
    assert "Population Statistics" not in html_report


def test_zip_results_contains_all_artifacts(make_upload, tiny_png):
    job_id = _seed_full_job(make_upload, tiny_png)
    names = set(zipfile.ZipFile(io.BytesIO(_zip_results(job_id))).namelist())
    assert names >= {
        "config.json",
        "kymographs/a.png",
        "collection/collection.mat",
        "collection/collection_postprocessed.json",
        "collection/collection_postprocessed.mat",
        "population.json",
        "trajectories.csv",
        "report.html",
    }

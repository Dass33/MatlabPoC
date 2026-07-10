from __future__ import annotations

import json

from connectors import storage


def test_create_job_writes_inputs_config_and_meta(make_upload):
    files = [make_upload("a.tif", b"tiff"), make_upload("a.txt", b"meta")]
    job_id = storage.create_job(files, {"foo": 1}, name="  My run  ")

    base, inp, out = storage.job_dirs(job_id)
    assert (inp / "a.tif").read_bytes() == b"tiff"
    assert (inp / "a.txt").read_bytes() == b"meta"
    assert out.is_dir()
    assert json.loads((base / "config.json").read_text()) == {"foo": 1}

    meta = json.loads((base / "meta.json").read_text())
    assert meta["job_id"] == job_id
    assert meta["name"] == "My run"  # stripped
    assert meta["filenames"] == ["a.tif", "a.txt"]
    assert meta["parent_job_id"] is None


def test_create_job_blank_name_is_none(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {}, name="   ")
    base, _, _ = storage.job_dirs(job_id)
    assert json.loads((base / "meta.json").read_text())["name"] is None


def test_create_job_writes_dark_cal_when_given(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {}, dark_cal_bytes=b"CAL")
    base, _, _ = storage.job_dirs(job_id)
    assert (base / "dark_cal.mat").read_bytes() == b"CAL"


def test_read_status_defaults_to_processing_when_missing(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {})
    assert storage.read_status(job_id) == {"status": "processing", "error": None}


def test_read_status_reads_written_status(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {})
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))
    assert storage.read_status(job_id)["status"] == "completed"


def test_read_status_handles_corrupt_file(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {})
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text("{not json")
    assert storage.read_status(job_id)["status"] == "unknown"


def _complete(job_id):
    _, _, out = storage.job_dirs(job_id)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))


def _set_submitted_at(job_id, value):
    base, _, _ = storage.job_dirs(job_id)
    meta = json.loads((base / "meta.json").read_text())
    meta["submitted_at"] = value
    (base / "meta.json").write_text(json.dumps(meta))


def test_list_jobs_sorted_and_completed_filter(make_upload):
    j_old = storage.create_job([make_upload("a.tif")], {}, name="first")
    j_new = storage.create_job([make_upload("b.tif")], {}, name="second")
    # Force distinct timestamps: create_job stamps to the second, so same-second
    # jobs would tie and a broken sort would still pass.
    _set_submitted_at(j_old, "2020-01-01T00:00:00")
    _set_submitted_at(j_new, "2025-01-01T00:00:00")
    _complete(j_new)

    all_jobs = storage.list_all_jobs()
    # most recent submitted_at first
    assert [j["job_id"] for j in all_jobs] == [j_new, j_old]

    completed = storage.list_completed_jobs()
    assert [j["job_id"] for j in completed] == [j_new]


def test_list_all_jobs_ignores_dirs_without_meta():
    (storage.DATA_DIR / "stray").mkdir()
    assert storage.list_all_jobs() == []


def test_clone_job_copies_inputs_and_records_parent(make_upload):
    src = storage.create_job(
        [make_upload("a.tif", b"raw"), make_upload("a.txt", b"m")],
        {"orig": True},
        dark_cal_bytes=b"CAL",
    )
    clone = storage.clone_job(src, {"orig": False}, name="clone")

    base, inp, _ = storage.job_dirs(clone)
    assert (inp / "a.tif").read_bytes() == b"raw"
    assert (base / "dark_cal.mat").read_bytes() == b"CAL"
    meta = json.loads((base / "meta.json").read_text())
    assert meta["parent_job_id"] == src
    assert json.loads((base / "config.json").read_text()) == {"orig": False}


def test_delete_job_removes_directory(make_upload):
    job_id = storage.create_job([make_upload("a.tif")], {})
    base, _, _ = storage.job_dirs(job_id)
    assert base.exists()
    storage.delete_job(job_id)
    assert not base.exists()

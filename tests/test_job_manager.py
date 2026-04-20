import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "streamlit"))


def _setup_job_manager(data_dir: Path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(data_dir))
    monkeypatch.setenv("HOST_DATA_DIR", str(data_dir))
    import importlib
    import job_manager
    importlib.reload(job_manager)
    return job_manager


def _write_meta(data_dir: Path, job_id: str, submitted_at: str = "2024-01-01T00:00:00"):
    job_dir = data_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    (job_dir / "meta.json").write_text(json.dumps({
        "job_id": job_id,
        "name": None,
        "filenames": [],
        "submitted_at": submitted_at,
        "started_at": submitted_at,
    }))
    return job_dir


# ── read_status ───────────────────────────────────────────────────────────────


def test_read_status_no_file_returns_processing(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "job_a")
    (tmp_path / "job_a" / "output").mkdir()

    status = jm.read_status("job_a")
    assert status["status"] == "processing"
    assert status["error"] is None


def test_read_status_completed(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "job_b")
    out = tmp_path / "job_b" / "output"
    out.mkdir(parents=True)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))

    status = jm.read_status("job_b")
    assert status["status"] == "completed"


def test_read_status_malformed_json_returns_unknown(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "job_c")
    out = tmp_path / "job_c" / "output"
    out.mkdir(parents=True)
    (out / "status.json").write_text("not valid json {{")

    status = jm.read_status("job_c")
    assert status["status"] == "unknown"


# ── list_all_jobs ─────────────────────────────────────────────────────────────


def test_list_all_jobs_empty_dir(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    assert jm.list_all_jobs() == []


def test_list_all_jobs_returns_jobs(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "job_1", "2024-01-01T10:00:00")
    _write_meta(tmp_path, "job_2", "2024-01-01T11:00:00")

    jobs = jm.list_all_jobs()
    assert len(jobs) == 2


def test_list_all_jobs_sorted_newest_first(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "old_job", "2024-01-01T08:00:00")
    _write_meta(tmp_path, "new_job", "2024-01-01T12:00:00")

    jobs = jm.list_all_jobs()
    assert jobs[0]["job_id"] == "new_job"
    assert jobs[1]["job_id"] == "old_job"


def test_list_all_jobs_skips_dirs_without_meta(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    _write_meta(tmp_path, "valid_job")
    (tmp_path / "orphan_dir").mkdir()

    jobs = jm.list_all_jobs()
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == "valid_job"


def test_list_completed_jobs_filters_correctly(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)

    _write_meta(tmp_path, "done_job")
    out = tmp_path / "done_job" / "output"
    out.mkdir(parents=True)
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))

    _write_meta(tmp_path, "running_job")

    completed = jm.list_completed_jobs()
    assert len(completed) == 1
    assert completed[0]["job_id"] == "done_job"


# ── job_dirs ──────────────────────────────────────────────────────────────────


def test_job_dirs_returns_correct_paths(tmp_path, monkeypatch):
    jm = _setup_job_manager(tmp_path, monkeypatch)
    base, inp, out = jm.job_dirs("test_job")
    assert base == tmp_path / "test_job"
    assert inp == tmp_path / "test_job" / "input"
    assert out == tmp_path / "test_job" / "output"

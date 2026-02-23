"""Unit tests for streamlit/job_manager.py."""
from __future__ import annotations

from job_manager import count_running_jobs, job_dirs, list_all_jobs, read_status


class TestJobDirs:
    def test_returns_base_input_output(self, data_dir):
        base, inp, out = job_dirs("my_job")
        assert base == data_dir / "my_job"
        assert inp == data_dir / "my_job" / "input"
        assert out == data_dir / "my_job" / "output"


class TestReadStatus:
    def test_no_status_file_returns_processing(self, data_dir):
        _, _, out = job_dirs("pending_job")
        out.mkdir(parents=True)
        result = read_status("pending_job")
        assert result["status"] == "processing"
        assert result["error"] is None

    def test_valid_status_file_is_parsed(self, data_dir):
        _, _, out = job_dirs("done_job")
        out.mkdir(parents=True)
        (out / "status.json").write_text('{"status": "completed", "error": null}')
        result = read_status("done_job")
        assert result["status"] == "completed"

    def test_malformed_json_returns_unknown(self, data_dir):
        _, _, out = job_dirs("bad_job")
        out.mkdir(parents=True)
        (out / "status.json").write_text("{not valid json")
        result = read_status("bad_job")
        assert result["status"] == "unknown"


class TestListAllJobs:
    def test_empty_data_dir_returns_empty(self, data_dir):
        assert list_all_jobs() == []

    def test_one_valid_job_returned(self, data_dir, job_dir):
        job_id, _ = job_dir
        _, _, out = job_dirs(job_id)
        (out / "status.json").write_text('{"status": "completed", "error": null}')
        jobs = list_all_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == job_id
        assert jobs[0]["status"] == "completed"

    def test_job_without_meta_json_is_skipped(self, data_dir):
        orphan = data_dir / "orphan_job"
        (orphan / "input").mkdir(parents=True)
        (orphan / "output").mkdir(parents=True)
        assert list_all_jobs() == []

    def test_corrupt_meta_skipped_others_still_returned(self, data_dir, job_dir):
        job_id, _ = job_dir
        corrupt = data_dir / "corrupt_job"
        corrupt.mkdir()
        (corrupt / "meta.json").write_text("{bad json")
        jobs = list_all_jobs()
        assert len(jobs) == 1
        assert jobs[0]["job_id"] == job_id

    def test_jobs_sorted_by_submitted_at_descending(self, data_dir):
        for ts in ("2024-01-01T10:00:00", "2024-01-01T12:00:00", "2024-01-01T11:00:00"):
            job_id = f"job_{ts.replace(':', '-')}"
            base = data_dir / job_id
            (base / "output").mkdir(parents=True)
            (base / "meta.json").write_text(
                f'{{"job_id": "{job_id}", "submitted_at": "{ts}"}}'
            )
        jobs = list_all_jobs()
        timestamps = [j["submitted_at"] for j in jobs]
        assert timestamps == sorted(timestamps, reverse=True)


class TestCountRunningJobs:
    def test_zero_when_no_jobs(self, data_dir):
        assert count_running_jobs() == 0

    def test_one_when_job_has_no_status_file(self, data_dir, job_dir):
        # No status.json → read_status returns "processing"
        assert count_running_jobs() == 1

    def test_two_processing_jobs(self, data_dir, job_dir):
        second_id = "20240101_130000_def456"
        base2 = data_dir / second_id
        (base2 / "output").mkdir(parents=True)
        (base2 / "meta.json").write_text(f'{{"job_id": "{second_id}", "submitted_at": "2024-01-01T13:00:00"}}')
        assert count_running_jobs() == 2

    def test_completed_job_not_counted(self, data_dir, job_dir):
        job_id, _ = job_dir
        _, _, out = job_dirs(job_id)
        (out / "status.json").write_text('{"status": "completed", "error": null}')
        assert count_running_jobs() == 0

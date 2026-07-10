from __future__ import annotations

import io
import json

from connectors import launcher


def test_log_tail_returns_last_bytes(tmp_path):
    p = tmp_path / "matlab.log"
    p.write_bytes(b"0123456789")
    assert launcher._log_tail(p, n_bytes=4) == "6789"


def test_log_tail_missing_file_returns_empty(tmp_path):
    assert launcher._log_tail(tmp_path / "nope.log") == ""


def test_fail_if_still_processing_marks_failed_when_no_status(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    log_dest = out / "matlab.log"
    log_dest.write_bytes(b"segfault details")

    launcher._fail_if_still_processing(out, returncode=139, log_dest=log_dest)

    status = json.loads((out / "status.json").read_text())
    assert status["status"] == "failed"
    assert "139" in status["error"]
    assert "segfault details" in status["error"]


def test_fail_if_still_processing_respects_terminal_status(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "status.json").write_text(json.dumps({"status": "completed", "error": None}))

    launcher._fail_if_still_processing(out, returncode=1, log_dest=out / "matlab.log")

    # must NOT overwrite a completed job
    assert json.loads((out / "status.json").read_text())["status"] == "completed"


def test_fail_if_still_processing_treats_corrupt_status_as_processing(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    (out / "status.json").write_text("{garbage")

    launcher._fail_if_still_processing(out, returncode=1, log_dest=out / "matlab.log")

    assert json.loads((out / "status.json").read_text())["status"] == "failed"


class FakeProc:
    def __init__(self, output: bytes, returncode: int):
        self.stdout = io.BytesIO(output)
        self.returncode = returncode
        self.waited = False

    def wait(self):
        self.waited = True


def test_reaper_writes_log_and_fails_on_nonzero_exit(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    log_dest = out / "matlab.log"
    proc = FakeProc(b"line1\nline2\n", returncode=1)

    launcher._process_reaper(proc, log_dest)  # type: ignore[arg-type]

    assert proc.waited
    assert log_dest.read_bytes() == b"line1\nline2\n"
    assert json.loads((out / "status.json").read_text())["status"] == "failed"


def test_reaper_does_not_fail_on_clean_exit(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    log_dest = out / "matlab.log"
    proc = FakeProc(b"done\n", returncode=0)

    launcher._process_reaper(proc, log_dest)  # type: ignore[arg-type]

    assert not (out / "status.json").exists()

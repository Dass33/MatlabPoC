from __future__ import annotations

import json

import idle
from connectors import launcher


class FakeProc:
    """Stand-in for subprocess.Popen: poll() returns None while running."""

    def __init__(self, returncode=None):
        self.returncode = returncode

    def poll(self):
        return self.returncode


def test_has_active_jobs_empty(monkeypatch):
    monkeypatch.setattr(launcher, "_active_procs", [])
    assert launcher.has_active_jobs() is False


def test_has_active_jobs_running(monkeypatch):
    monkeypatch.setattr(launcher, "_active_procs", [FakeProc(None)])
    assert launcher.has_active_jobs() is True


def test_has_active_jobs_prunes_finished(monkeypatch):
    procs = [FakeProc(0), FakeProc(1)]
    monkeypatch.setattr(launcher, "_active_procs", procs)
    assert launcher.has_active_jobs() is False
    assert procs == []


def test_has_active_jobs_mixed_keeps_running(monkeypatch):
    running = FakeProc(None)
    procs = [FakeProc(0), running]
    monkeypatch.setattr(launcher, "_active_procs", procs)
    assert launcher.has_active_jobs() is True
    assert procs == [running]


def test_write_probe_reports_job_state(tmp_path, monkeypatch):
    monkeypatch.setattr(idle, "STATIC_DIR", tmp_path / "static")

    monkeypatch.setattr(idle, "has_active_jobs", lambda: True)
    idle.write_probe()
    probe = tmp_path / "static" / "idle_probe.json"
    assert json.loads(probe.read_text()) == {"job_running": True}

    monkeypatch.setattr(idle, "has_active_jobs", lambda: False)
    idle.write_probe()
    assert json.loads(probe.read_text()) == {"job_running": False}
    assert not probe.with_suffix(".json.tmp").exists()

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


class FakeSession:
    def __init__(self, sid):
        self.id = sid
        self.reruns = 0

    def request_rerun(self, client_state):
        self.reruns += 1


class FakeSessionInfo:
    def __init__(self, sid, run_count):
        self.session = FakeSession(sid)
        self.script_run_count = run_count


def _patch_sessions(monkeypatch, infos):
    class FakeMgr:
        def list_active_sessions(self):
            return infos

    class FakeRuntime:
        _session_mgr = FakeMgr()

    monkeypatch.setattr("streamlit.runtime.get_instance", lambda: FakeRuntime())


def test_zombie_kicked_only_on_second_scan(monkeypatch):
    zombie = FakeSessionInfo("z1", 0)
    _patch_sessions(monkeypatch, [zombie])
    pending, kicked = set(), set()

    pending = idle.kick_zombie_sessions(pending, kicked)
    assert pending == {"z1"} and zombie.session.reruns == 0

    pending = idle.kick_zombie_sessions(pending, kicked)
    assert zombie.session.reruns == 1 and kicked == {"z1"}

    # never kicked twice
    pending = idle.kick_zombie_sessions(pending, kicked)
    assert zombie.session.reruns == 1


def test_active_sessions_never_kicked(monkeypatch):
    active = FakeSessionInfo("a1", 3)
    _patch_sessions(monkeypatch, [active])
    pending = idle.kick_zombie_sessions(set(), set())
    pending = idle.kick_zombie_sessions(pending, set())
    assert active.session.reruns == 0 and pending == set()


def test_session_that_ran_between_scans_not_kicked(monkeypatch):
    info = FakeSessionInfo("s1", 0)
    _patch_sessions(monkeypatch, [info])
    pending = idle.kick_zombie_sessions(set(), set())
    info.script_run_count = 1
    pending = idle.kick_zombie_sessions(pending, set())
    assert info.session.reruns == 0

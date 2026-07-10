from __future__ import annotations

import json
import logging
import subprocess
import threading
from pathlib import Path

from env import MATLAB_APP, MCR_ROOT, job_dirs

log = logging.getLogger(__name__)

# MATLAB binary runs as a different user inside the container; all job output
# files need to be accessible by the Streamlit process after the job completes.
_JOB_DIR_MODE = 0o777

# Live MATLAB subprocesses launched by this process. Used by the idle probe to
# decide whether the container may be disconnected and scaled to zero. Tracked
# as processes (not status.json) so a stale "processing" status left behind by
# an earlier container can never keep the instance alive forever.
_active_procs: list[subprocess.Popen] = []
_active_lock = threading.Lock()


def has_active_jobs() -> bool:
    """True while any MATLAB job subprocess is still running."""
    with _active_lock:
        _active_procs[:] = [p for p in _active_procs if p.poll() is None]
        return bool(_active_procs)


def _log_tail(log_dest: Path, n_bytes: int = 2000) -> str:
    try:
        return log_dest.read_bytes()[-n_bytes:].decode("utf-8", errors="replace")
    except OSError:
        return ""


def _fail_if_still_processing(out: Path, returncode: int, log_dest: Path) -> None:
    """If MATLAB crashed without writing a terminal status, mark the job failed.

    Covers segfault / OOM-kill / failed start — cases where MATLAB's own catch
    block never runs, which would otherwise leave the job 'processing' forever.
    """
    status_file = out / "status.json"
    current = "processing"
    if status_file.exists():
        try:
            current = json.loads(status_file.read_text()).get("status", "processing")
        except (json.JSONDecodeError, OSError):
            pass
    if current != "processing":
        return

    tail = _log_tail(log_dest)
    error = f"MATLAB process exited with code {returncode} without reporting status."
    if tail:
        error += f"\n\nLast output:\n{tail}"
    tmp = status_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"status": "failed", "error": error}))
    tmp.replace(status_file)
    log.error("[reaper] job marked failed (exit=%s): %s", returncode, out.parent.name)


def _process_reaper(proc: subprocess.Popen, log_dest: Path) -> None:
    try:
        stdout = proc.stdout
        assert stdout is not None
        with open(log_dest, "wb") as f:
            for line in iter(stdout.readline, b""):
                f.write(line)
                f.flush()
        proc.wait()
        for p in [log_dest.parent, *log_dest.parent.rglob("*")]:
            try:
                p.chmod(_JOB_DIR_MODE)
            except OSError:
                pass
        if proc.returncode != 0:
            _fail_if_still_processing(log_dest.parent, proc.returncode, log_dest)
    except (OSError, ValueError) as e:
        log.error("[reaper] %s", e)


def launch_matlab_job(job_id: str) -> None:
    _, inp, out = job_dirs(job_id)
    out.mkdir(parents=True, exist_ok=True)

    log.info("[launch] job=%s inp=%s out=%s", job_id, inp, out)

    proc = subprocess.Popen(
        [MATLAB_APP, MCR_ROOT, str(inp), str(out)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(Path(MATLAB_APP).parent),
    )
    log.info("[launch] pid=%s", proc.pid)

    with _active_lock:
        _active_procs.append(proc)

    threading.Thread(
        target=_process_reaper,
        args=(proc, out / "matlab.log"),
        daemon=True,
    ).start()

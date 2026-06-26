from __future__ import annotations

import logging
import subprocess
import threading
from pathlib import Path

from env import MATLAB_APP, MCR_ROOT, job_dirs

log = logging.getLogger(__name__)


def _process_reaper(proc: subprocess.Popen, log_dest: Path) -> None:
    try:
        stdout, _ = proc.communicate()
        log_dest.write_bytes(stdout)
        for p in [log_dest.parent, *log_dest.parent.rglob("*")]:
            try:
                p.chmod(0o777)
            except OSError:
                pass
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

    threading.Thread(
        target=_process_reaper,
        args=(proc, out / "matlab.log"),
        daemon=True,
    ).start()

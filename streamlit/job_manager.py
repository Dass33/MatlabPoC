from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

_TZ = ZoneInfo("Europe/Prague")

log = logging.getLogger(__name__)

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data/jobs"))
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "5"))
MCR_ROOT = os.environ.get("MCR_ROOT", "/opt/matlabruntime/R2025b")
MATLAB_APP = os.environ.get("MATLAB_APP", "/opt/matlab_app/run_AnalyzeExperimentApp.sh")

DATA_DIR.mkdir(parents=True, exist_ok=True)


def job_dirs(job_id: str) -> tuple[Path, Path, Path]:
    """Return (base, input, output) paths for a given job."""
    base = DATA_DIR / job_id
    return base, base / "input", base / "output"


def read_status(job_id: str) -> dict:
    _, _, out = job_dirs(job_id)
    status_file = out / "status.json"
    if not status_file.exists():
        return {"status": "processing", "error": None}
    try:
        return json.loads(status_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        log.error("[read_status] %s: %s", job_id, e)
        return {"status": "unknown", "error": "Could not read status.json"}


def list_all_jobs() -> list[dict]:
    """Scan DATA_DIR for all jobs with meta.json, sorted by submission date descending."""
    jobs = []
    if not DATA_DIR.exists():
        return jobs
    for job_dir in DATA_DIR.iterdir():
        if not job_dir.is_dir():
            continue
        meta_file = job_dir / "meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text())
            status = read_status(job_dir.name)
            meta["status"] = status["status"]
            meta["error"] = status.get("error")
            jobs.append(meta)
        except (json.JSONDecodeError, OSError, KeyError) as e:
            log.warning("[list_all_jobs] skipping %s: %s", job_dir.name, e)
            continue
    return sorted(jobs, key=lambda j: j.get("submitted_at", ""), reverse=True)


def stream_upload_to_disk(uploaded_file, dest_path: Path) -> None:
    uploaded_file.seek(0)
    with open(dest_path, "wb") as f:
        shutil.copyfileobj(uploaded_file, f, length=8 * 1024 * 1024)


def _process_reaper(proc: subprocess.Popen, log_dest: Path) -> None:
    try:
        stdout, _ = proc.communicate()
        log_dest.write_bytes(stdout)
        for p in [log_dest.parent, *log_dest.parent.rglob("*")]:
            try:
                p.chmod(0o777)
            except OSError:
                pass
    except Exception as e:
        log.error("[reaper] %s", e)


def launch_matlab_job(job_id: str) -> None:
    """Run the compiled MATLAB algorithm as a subprocess."""
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


def list_completed_jobs() -> list[dict]:
    """Return only jobs with status 'completed'."""
    return [j for j in list_all_jobs() if j["status"] == "completed"]


def submit_job(
    uploaded_files: list,
    config: dict,
    dark_cal_bytes: bytes | None = None,
    name: str = "",
) -> str:
    """Write uploaded files to disk, save config/meta, and launch MATLAB analysis. Returns job_id."""
    job_id = datetime.now(_TZ).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    base, inp, out = job_dirs(job_id)
    inp.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    filenames = []
    for uf in uploaded_files:
        stream_upload_to_disk(uf, inp / uf.name)
        filenames.append(uf.name)

    if dark_cal_bytes is not None:
        (base / "dark_cal.mat").write_bytes(dark_cal_bytes)

    (base / "config.json").write_text(json.dumps(config, indent=2))
    now = datetime.now(_TZ).isoformat(timespec="seconds")
    (base / "meta.json").write_text(
        json.dumps(
            {
                "job_id": job_id,
                "name": name.strip() or None,
                "filenames": filenames,
                "submitted_at": now,
                "started_at": now,
            },
            indent=2,
        )
    )

    launch_matlab_job(job_id)
    return job_id

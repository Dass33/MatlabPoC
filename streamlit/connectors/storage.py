from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime

from paths import DATA_DIR, TZ, job_dirs

log = logging.getLogger(__name__)


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


def list_completed_jobs() -> list[dict]:
    return [j for j in list_all_jobs() if j["status"] == "completed"]


def create_job(
    uploaded_files: list,
    config: dict,
    dark_cal_bytes: bytes | None = None,
    name: str = "",
) -> str:
    """Write job files to disk and return the new job_id. Does not launch the job."""
    job_id = datetime.now(TZ).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    base, inp, out = job_dirs(job_id)
    inp.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    filenames = []
    for uf in uploaded_files:
        uf.seek(0)
        with open(inp / uf.name, "wb") as f:
            shutil.copyfileobj(uf, f, length=8 * 1024 * 1024)
        filenames.append(uf.name)

    if dark_cal_bytes is not None:
        (base / "dark_cal.mat").write_bytes(dark_cal_bytes)

    (base / "config.json").write_text(json.dumps(config, indent=2))
    now = datetime.now(TZ).isoformat(timespec="seconds")
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
    return job_id

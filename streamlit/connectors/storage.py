from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import datetime

from env import DATA_DIR, DEMO_DATA_DIR, TZ, job_dirs

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


def _new_job_id() -> str:
    return datetime.now(TZ).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def _write_job(
    base,
    job_id: str,
    config: dict,
    filenames: list[str],
    name: str,
    parent_job_id: str | None = None,
) -> None:
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
                "parent_job_id": parent_job_id,
            },
            indent=2,
        )
    )


def create_job(
    uploaded_files: list,
    config: dict,
    dark_cal_bytes: bytes | None = None,
    name: str = "",
) -> str:
    """Write job files to disk and return the new job_id. Does not launch the job."""
    job_id = _new_job_id()
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

    _write_job(base, job_id, config, filenames, name)
    return job_id


def clone_job(source_job_id: str, config: dict, name: str = "") -> str:
    """Copy a completed job's input files into a new job with a (possibly edited) config."""
    job_id = _new_job_id()
    base, inp, out = job_dirs(job_id)
    src_base, src_inp, _ = job_dirs(source_job_id)

    shutil.copytree(src_inp, inp)
    out.mkdir(parents=True, exist_ok=True)
    filenames = sorted(f.name for f in inp.iterdir())

    src_dark_cal = src_base / "dark_cal.mat"
    if src_dark_cal.exists():
        shutil.copy(src_dark_cal, base / "dark_cal.mat")

    _write_job(base, job_id, config, filenames, name, parent_job_id=source_job_id)
    return job_id


def create_demo_job(config: dict, name: str = "Demo experiment") -> str:
    """Load the bundled demo TIFF+txt pairs into a new job."""
    job_id = _new_job_id()
    base, inp, out = job_dirs(job_id)
    inp.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    filenames = []
    for f in sorted(DEMO_DATA_DIR.glob("*")):
        if f.is_file():
            shutil.copy(f, inp / f.name)
            filenames.append(f.name)

    _write_job(base, job_id, config, filenames, name)
    return job_id


def delete_job(job_id: str) -> None:
    base, _, _ = job_dirs(job_id)
    if base.exists() and base.is_dir():
        shutil.rmtree(base)

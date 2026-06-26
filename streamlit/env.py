from __future__ import annotations

import os
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")
DATA_DIR = Path(os.environ.get("DATA_DIR", "./data/jobs"))
POLL_INTERVAL_S = int(os.environ.get("POLL_INTERVAL_S", "5"))
MCR_ROOT = os.environ.get("MCR_ROOT", "/opt/matlabruntime/R2025b")
MATLAB_APP = os.environ.get(
    "MATLAB_APP", "/opt/matlab_app/run_AnalyzeExperimentApp.sh"
)

DATA_DIR.mkdir(parents=True, exist_ok=True)


def job_dirs(job_id: str) -> tuple[Path, Path, Path]:
    base = DATA_DIR / job_id
    return base, base / "input", base / "output"

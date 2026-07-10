"""Idle-disconnect probe.

Background thread periodically writes the current job state
to a file that Streamlit serves statically,
and the watchdog fetches it at idle-timeout time.

Requires `server.enableStaticServing=true`
The file is served at <base>/app/static/idle_probe.json.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path

from connectors.launcher import has_active_jobs

log = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"
PROBE_INTERVAL_S = 15


def write_probe() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    probe_file = STATIC_DIR / "idle_probe.json"
    tmp = probe_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"job_running": has_active_jobs()}))
    tmp.replace(probe_file)


def _probe_loop() -> None:
    while True:
        try:
            write_probe()
        except OSError as e:
            log.warning("[idle-probe] %s", e)
        time.sleep(PROBE_INTERVAL_S)


def start_probe_writer() -> None:
    """Start the probe-writer thread. Call once per process."""
    threading.Thread(target=_probe_loop, daemon=True).start()

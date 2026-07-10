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

_started = False
_started_lock = threading.Lock()


def write_probe() -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    probe_file = STATIC_DIR / "idle_probe.json"
    tmp = probe_file.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"job_running": has_active_jobs()}))
    tmp.replace(probe_file)


def kick_zombie_sessions(pending: set[str], kicked: set[str]) -> set[str]:
    """Force one rerun for sessions whose script has never run.

    A tab that loaded the page against an older server never sends a rerun
    request when it reconnects: the server creates a session, no script runs,
    and the websocket idles forever - so such tabs would never receive the
    idle watchdog. Requesting a rerun server-side pushes a current element
    tree (watchdog included) into the old page.

    A session is only kicked when it was already at zero runs on the previous
    scan, so a normal page load (which requests its own rerun within
    milliseconds) is never touched. Returns the new pending set.
    """
    from streamlit.runtime import get_instance

    still_zero = set()
    for info in get_instance()._session_mgr.list_active_sessions():
        if getattr(info, "script_run_count", 1) != 0:
            continue
        sid = info.session.id
        if sid in kicked:
            continue
        if sid in pending:
            kicked.add(sid)
            info.session.request_rerun(None)
            log.info("[idle-probe] kicked zombie session %s", sid)
        else:
            still_zero.add(sid)
    return still_zero


def _probe_loop() -> None:
    pending: set[str] = set()
    kicked: set[str] = set()
    while True:
        try:
            write_probe()
        except OSError as e:
            log.warning("[idle-probe] %s", e)
        try:
            pending = kick_zombie_sessions(pending, kicked)
        except Exception as e:
            # Touches Streamlit internals (_session_mgr, script_run_count);
            # never let a version change take the probe thread down with it.
            log.warning("[idle-probe] zombie kick failed: %s", e)
        time.sleep(PROBE_INTERVAL_S)


def start_probe_writer() -> None:
    """Start the probe-writer thread. Idempotent per process.

    Called from serve.py at server start (containers) and as a fallback from
    main.py on the first script run (plain `streamlit run` in development).
    """
    global _started
    with _started_lock:
        if _started:
            return
        _started = True
    threading.Thread(target=_probe_loop, daemon=True).start()

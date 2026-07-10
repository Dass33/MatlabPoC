#!/usr/bin/env python3
"""End-to-end check of the idle-disconnect machinery against legacy tabs.

Reproduces the production incident where a tab that loaded the page before
the idle feature existed reconnected forever without ever running a script
(a "zombie" session), so it never received the browser watchdog and kept the
Cloud Run instance alive indefinitely:

1. Start the app with idle disconnect OFF and open a real (headless) browser
   tab - this tab has no watchdog, like a tab from an old deployment.
2. Kill the server and start a new one WITH idle disconnect, via serve.py,
   exactly like the container does.
3. The tab reconnects but does not rerun the script; the probe thread must
   detect the zombie session and force a rerun (idle.kick_zombie_sessions),
   which delivers the watchdog.
4. The watchdog must then disconnect the idle tab to the static page.

Run this after upgrading streamlit: both the zombie kicker and serve.py use
streamlit-internal APIs (_session_mgr, script_run_count,
config._config_options_template) that can change between versions.

Requires: pip install playwright && python -m playwright install chromium
Usage: streamlit/venv/bin/python scripts/check_legacy_reconnect.py
"""

from __future__ import annotations

import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = 8517
IDLE_TIMEOUT_S = 10


def start_server(idle_timeout: int) -> subprocess.Popen:
    proc = subprocess.Popen(
        [str(ROOT / "streamlit/venv/bin/python"), str(ROOT / "streamlit/serve.py")],
        env={
            "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()),
            "IDLE_TIMEOUT_S": str(idle_timeout),
            "STREAMLIT_SERVER_ENABLE_STATIC_SERVING": "true",
            "STREAMLIT_SERVER_HEADLESS": "true",
            "STREAMLIT_SERVER_PORT": str(PORT),
        },
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(120):
        time.sleep(0.5)
        try:
            urllib.request.urlopen(f"http://localhost:{PORT}/_stcore/health", timeout=1)
            return proc
        except OSError:
            continue
    raise RuntimeError("server did not start")


def main() -> int:
    from playwright.sync_api import sync_playwright

    srv = start_server(0)
    print("[1] server A up (idle OFF)")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page()
            page.goto(f"http://localhost:{PORT}/", wait_until="networkidle")
            time.sleep(3)
            v = page.evaluate("() => window.__nsmIdleWatchdogVersion")
            assert v is None, f"watchdog unexpectedly present: {v}"
            print("[2] legacy tab open, no watchdog")

            srv.terminate()
            srv.wait()
            time.sleep(2)
            srv = start_server(IDLE_TIMEOUT_S)
            print("[3] server B up (idle ON) - waiting for kick + disconnect")

            deadline = time.time() + 120
            while time.time() < deadline:
                time.sleep(3)
                url = page.evaluate("() => location.href")
                if "disconnected" in url:
                    print(f"[4] PASS: legacy tab disconnected -> {url}")
                    browser.close()
                    return 0
            v = page.evaluate("() => window.__nsmIdleWatchdogVersion")
            print(f"[4] FAIL: still connected after 120s (watchdog version: {v})")
            browser.close()
            return 1
    finally:
        srv.terminate()
        srv.wait()


if __name__ == "__main__":
    sys.exit(main())

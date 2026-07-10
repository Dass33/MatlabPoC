"""Browser-side idle watchdog.

See idle.py for the server-side probe this watchdog polls, and
docs/reasoning.md (Architectural Decisions no. 5) for the design history.
"""

from __future__ import annotations

import streamlit.components.v1 as st_components


def render_idle_watchdog(idle_timeout_s: int) -> None:
    """Disconnect idle browsers.

    After idle_timeout_s without user input the watchdog fetches the idle
    probe (see idle.py).
    If no MATLAB job is running it navigates the tab to
    a static "disconnected" page, which closes the websocket.
    """
    st_components.html(
        f"""
        <script>
        function nsmIdleWatchdog(cfg) {{
            let timer = null;
            let probeFailures = 0;

            function arm(delayMs) {{
                clearTimeout(timer);
                timer = setTimeout(onIdle, delayMs);
            }}
            function reset() {{ arm(cfg.idleMs); }}

            async function onIdle() {{
                let jobRunning = false;
                let probeOk = false;
                try {{
                    const url = new URL('./app/static/idle_probe.json', location.href);
                    const resp = await fetch(url, {{cache: 'no-store'}});
                    if (resp.ok) {{
                        jobRunning = (await resp.json()).job_running === true;
                        probeOk = true;
                    }}
                }} catch (e) {{ /* fall through to failure handling */ }}

                if (jobRunning) {{
                    probeFailures = 0;
                    arm(cfg.recheckMs);
                    return;
                }}
                // If the probe is unreadable, assume a job might be running and
                // retry a few times before giving up and disconnecting anyway.
                if (!probeOk && ++probeFailures < cfg.maxProbeFailures) {{
                    arm(cfg.recheckMs);
                    return;
                }}
                location.href = new URL('./app/static/disconnected.xml', location.href);
            }}

            // Only events a physical input device can produce: Streamlit
            const events = ['mousemove', 'mousedown', 'touchstart', 'touchmove', 'click', 'keydown', 'wheel'];
            events.forEach(ev => window.addEventListener(ev, reset, {{capture: true, passive: true}}));
            window.__nsmIdleWatchdogDispose = () => {{
                clearTimeout(timer);
                events.forEach(ev => window.removeEventListener(ev, reset, {{capture: true}}));
            }};
            reset();
        }}

        // Versioned so a redeploy can replace a watchdog already injected into
        // a long-lived page
        const WATCHDOG_VERSION = 2;
        const p = window.parent;
        if (p.__nsmIdleWatchdogVersion !== WATCHDOG_VERSION) {{
            p.__nsmIdleWatchdogVersion = WATCHDOG_VERSION;
            const cfg = {{
                idleMs: {idle_timeout_s * 1000},
                recheckMs: 60000,
                maxProbeFailures: 5,
            }};
            const s = p.document.createElement('script');
            s.textContent =
                'if (window.__nsmIdleWatchdogDispose) window.__nsmIdleWatchdogDispose();' +
                '(' + nsmIdleWatchdog.toString() + ')(' + JSON.stringify(cfg) + ');';
            p.document.head.appendChild(s);
            s.remove();
        }}
        </script>
        """,
        height=0,
    )

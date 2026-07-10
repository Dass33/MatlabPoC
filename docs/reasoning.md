# Architectural Decisions & Rationale

This document tracks major design choices made throughout the development of the NSM Data Processing application, including their associated trade-offs.

---

## 1. Reusing the Matlab Code

*   **Decision**: Reuse the existing MATLAB algorithms directly via compilation, rather than rewriting them in Python/C++.
*   **Rationale**: The algorithm is complex and changes frequently. Maintaining dual implementations (one in MATLAB for research and one in another language for production) would double development overhead and risk code drift.
*   **Trade-off**: Spawning a MATLAB compiled binary requires the MATLAB Runtime (MCR) to be installed, which makes Docker image size about 10GB and introduces startup latency. However, it requires no runtime license fees.

---

## 2. Choosing Streamlit for the Web UI

*   **Decision**: Implement the user interface as a single-page Streamlit Python application.
*   **Rationale**: Streamlit makes it very easy and fast to create dashboard interfaces and is very friendly to newcomers to web dev.
*   **Trade-off**: Streamlit is heavily opinionated, and doing custom components in it requires more effort.

---

## 3. Using docker

*   **Decision**: Use docker contianer to boundle our application.
*   **Rationale**: It makes it way eaiser to deploy to different machines.
    **Trade-off**: Slower iteration development speed, storage overhead due to matlab runtime big size.

## 4. Using file system instead of DB

*   **Decision**: TODO
*   **Rationale**: TODO
    **Trade-off**: TODO

---

## 5. Idle disconnect of browser tabs

*   **Decision**: Disconnect browsers after `IDLE_TIMEOUT_S` without user input (default 30 min, `0` = off), but never while a MATLAB job runs. A page watchdog (`streamlit/main.py`) checks a probe file written by a server thread (`streamlit/idle.py`) and navigates the tab to a static page, closing the websocket.
*   **Rationale**: An open Streamlit tab holds a websocket forever, which on pay-per-use hosting (Cloud Run) keeps the instance alive and billing. One forgotten tab kept the service running for ~36 hours. The mechanism is host-independent: it simply sheds dead connections, whatever the deployment.
*   **Trade-off**: Surprising for users who return to a disconnected tab (one click reconnects), and it took several attempts to get right - see lessons below.

Lessons learned while building it (all cost a failed deploy or hours of log digging):

1.  **Component iframes cannot navigate the tab.** `st.components.v1.html` runs in a sandbox without `allow-top-navigation`; the naive `window.parent.location = ...` fails silently. The watchdog injects itself into the parent page instead (possible because the sandbox grants `allow-same-origin`).
2.  **"User activity" must mean physical input only.** Listening to `scroll` never fires the timer on pages with periodically re-rendering charts - re-renders emit synthetic scroll events. Listen to `wheel`/`touchmove`/`mousemove`/`keydown` instead.
3.  **Old tabs reconnect but never rerun the script** ("zombie" sessions): the server creates a session, no script runs, nothing new is ever delivered - so a fix shipped in the app never reaches the tabs that need it, and they hold the websocket forever. The probe thread force-reruns such sessions (`kick_zombie_sessions`), and the container starts through `streamlit/serve.py` instead of `streamlit run` so that thread exists even when only zombies are connected.
4.  **Streamlit static serving whitelists content types.** `.html` is served as `text/plain`; the disconnected page is XHTML named `.xml`.
5.  The kicker and `serve.py` touch Streamlit-internal APIs; after a streamlit upgrade run `scripts/check_legacy_reconnect.py` (playwright) which replays the whole zombie scenario against a real browser.

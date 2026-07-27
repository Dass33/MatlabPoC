# Streamlit Frontend Overview

The application frontend is structured as a multi-tab Streamlit dashboard. The entry point of the app is `streamlit/main.py`.

It imports page modules corresponding to each stage of the analysis workflow:
1. **Submit**: For uploading files and launching background MATLAB jobs.
2. **Kymograph**: To inspect raw uploaded kymograph images.
3. **Post-processing**: For outlier filtering and IOC calibration.
4. **Population**: For statistics.
5. **Overview**: For managing and retrieving past jobs.
6. **Help**: Instructions for researchers.

Alongside the tabs there is the parameter sidebar, whose widgets are generated from the selected
[preset](presets.md), and the [preset editor](presets.md) behind `?preset-editor=on` where those
presets are curated.

---

## Technical Architecture

Streamlit executes the script from top to bottom on every user interaction. To retain state across tabs, the app utilizes `st.session_state` to store job configurations, status info, overrides, and results in-memory.

---

## Code Reference

::: main

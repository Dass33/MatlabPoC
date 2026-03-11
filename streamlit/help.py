import streamlit as st
from job_manager import MAX_WORKERS


def page_help():
    st.markdown(f"""
        ### How to use

        1. Configure algorithm parameters in the sidebar.
        2. Upload your `.tiff` files **and their paired `.txt` metadata files** in the **Submit** tab.
           Each TIFF must have a matching TXT with the same base name (e.g. `data_001.tiff` + `data_001.txt`).
        3. Click **Submit job**. Files are written to disk immediately and the
           MATLAB container starts in the background — your browser does not need
           to stay open.
        4. Enable **Wait for result** if you prefer to watch progress on this page.
        5. Once complete, results appear in the **History** tab. All users share
           the same history.

        ### Output files

        | File | Contents |
        |------|----------|
        | `kymographs/*.png` | Kymograph images with track overlays |
        | `trajectories.mat` | Per-trajectory: iOC, D, velocity, N, positionStart, positionEnd |
        | `summary.json` | Population statistics per sweep (MEAN, FWHM, RESOLUTION) |
        | `results.mat` | Full archive for MATLAB post-processing |

        ### Worker slots

        There are **{MAX_WORKERS}** concurrent MATLAB worker slots. If both are busy,
        wait for one to finish.
        """)

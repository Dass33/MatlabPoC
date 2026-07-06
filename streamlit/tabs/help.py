import streamlit as st


def page_help() -> None:
    """Help tab — static usage instructions and output file reference."""
    st.markdown("""
        ### Documentation
        Link to app documentation: [here](https://dass33.github.io/MatlabPoC/)

        ### App walkthrough

        1. Configure algorithm parameters in the sidebar. Use **Load config** to reuse a saved
           preset or an exported config file, and **Save preset / config** to keep your own.
        2. **Submit** tab:  upload your `.tiff` files **and their paired `.txt` metadata files**.
           Each TIFF must have a matching TXT with the same base name (e.g. `data_001.tiff` + `data_001.txt`).
        3. Click **Submit job**. Files are written to disk immediately and the container starts in the background,
           your browser does not need to stay open.
        4. Enable **Wait for result** if you prefer to watch progress on this page — kymographs
           appear here one by one as MATLAB finishes each one.
        5. Once complete, select the experiment from the dropdown at the top of the page, then work
           through **Post-processing** (review thresholds, inspect trajectories, **Accept & Save**) and
           **Population Analysis** (**Run Population Analysis**).
        6. In **Population Analysis**, use **Compare experiments** to overlay 2–3 completed
           experiments' results. In **Overview**, use **Clone & Re-run** to re-analyze a job's
           inputs with a tweaked config, or download results.

        ---

        ### Output files

        | File | Contents |
        |------|----------|
        | `kymographs/*.png` | Kymograph images |
        | `collection/collection.mat` | Raw trajectory collection |
        | `collection_postprocessed.json` | Filtered collection after post-processing |
        | `population.json` | Population statistics after population analysis |
        | `status.json` | Job status and error message if failed |

        The downloadable results ZIP (from **Overview**) additionally bundles a `trajectories.csv`
        (per-trajectory properties, Excel/Origin-friendly), a `collection_postprocessed.mat`
        (curated collection for MATLAB), and a self-contained `report.html` summary.

        ---

        ### Post-processing

        The scatter plot shows all trajectories coloured by state:
        - **auto-kept** — passes the configured outlier thresholds
        - **auto-excluded** — rejected by outlier thresholds
        - **manual-kept / manual-excluded** — overridden by lasso/box selection

        **Trajectory inspector** — click any point in the scatter to open an inspector right below
        the curation buttons. It shows that trajectory's key numbers (iOC/STDiOC in µ, N, D,
        velocity), its position-over-time trace, and its iOC profile — everything you need to judge
        whether a point is a real particle or a tracking artifact before deciding to exclude it. The
        inspected trajectory is also highlighted in white in the kymograph track preview below. To
        select several trajectories at once for **Include/Exclude selected**, switch to the lasso or
        box-select tool in the chart's toolbar (the default click tool is for panning/inspecting).

        Use the threshold table to adjust per-property thresholds (`3std`, `3std_conditional`, or a fixed number).
        Click **Accept & Save** when satisfied — this writes `collection_postprocessed.json` and optionally
        runs iOC calibration before handing off to Population Analysis.
        """)

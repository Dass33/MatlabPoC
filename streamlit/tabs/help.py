import streamlit as st


def page_help() -> None:
    """Help tab — static usage instructions and output file reference."""
    st.markdown("""
        ### Documnetation
        Link to app documentation: [here](https://dass33.github.io/MatlabPoC/)

        ### App walkthrough

        1. Configure algorithm parameters in the sidebar
        2. **Submit** tab:  upload your `.tiff` files **and their paired `.txt` metadata files**.
           Each TIFF must have a matching TXT with the same base name (e.g. `data_001.tiff` + `data_001.txt`).
        3. Click **Submit job**. Files are written to disk immediately and the container starts in the background,
           your browser does not need to stay open.
        4. Enable **Wait for result** if you prefer to watch progress on this page.
        5. Once complete, select the experiment from the dropdown at the top of the page, then work
           through **Post-processing** (review thresholds, **Accept & Save**) and **Population
           Analysis** (**Run Population Analysis**).
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

        ---

        ### Post-processing

        The scatter plot shows all trajectories coloured by state:
        - **auto-kept** — passes the configured outlier thresholds
        - **auto-excluded** — rejected by outlier thresholds
        - **manual-kept / manual-excluded** — overridden by lasso/box selection

        Use the threshold table to adjust per-property thresholds (`3std`, `3std_conditional`, or a fixed number).
        Click **Accept & Save** when satisfied — this writes `collection_postprocessed.json` and optionally
        runs iOC calibration before handing off to Population Analysis.
        """)

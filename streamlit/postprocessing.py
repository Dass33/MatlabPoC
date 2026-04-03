"""
Outlier Filtering
Per-property threshold configuration: each property gets its own σ value and direction (upper/lower/both). Not a single global direction.
Lasso tool with three modes: exclude, include, deselect (clear override). Implemented via st.plotly_chart with on_select.
Four trajectory states with four distinct colors: auto-kept, auto-excluded, manual-kept, manual-excluded.
Manual overrides always win over threshold-based classification.
Manual overrides are session-only (st.session_state). Not persisted to disk. The final classification is baked into collection_postprocessed.mat on accept.
iOC calibration runs in Python (reimplemented from MATLAB). Produces A(x), Astd(x), AN(x) curves.
Use st.fragment for partial re-rendering on slider changes.
"""


def page_postprocessing() -> None:
    return

# Post-processing Tab

It loads completed job data (`collection.mat`), allows researchers to adjust outlier filters, inspect individual trajectories, and perform iOC calibration.

---

## Technical Workflows

### 1. Outlier Filtering
Raw molecular trajectories contain noise or artifacts (such as dust or aggregated particles) that can skew the final physical conclusions. 
*   Researchers select which physical property to filter on (e.g., `N`, `iOC`, `D`, or `velocity`).
*   They choose standard deviation thresholds (e.g., `mean ± 3 * STD`) or custom numeric limits.
*   The system calls `matlab_bridge.find_outliers` to compute a boolean keep/discard mask and renders interactive scatter plots using **Plotly**.

### 2. Trajectory Inspector
Clicking a point in the scatter plot opens an inspector below the curation buttons for that
trajectory: its scalar properties (iOC/STDiOC in µ, N, D, velocity), its position-vs-time trace,
and its iOC profile. This lets researchers judge whether an outlier is a real particle or a
tracking artifact before excluding it. The inspected trajectory is also highlighted in white in
the kymograph track preview. The chart's default tool is pan/click-to-inspect; switch to the
lasso or box-select tool in the chart toolbar to select multiple trajectories for bulk
include/exclude.

### 3. iOC Calibration
Interferometric Scattering Microscopy detects signal contrast ($iOC$). To map these values to actual molecular weights or refractive indices, a calibration is required:
*   A polynomial or linear regression calibration curve is fitted to the data.
*   Once calculated, values are updated in the data structures in-memory, and the resulting calibrated dataset can be downloaded.

---

## Code Reference

::: tabs.postprocessing

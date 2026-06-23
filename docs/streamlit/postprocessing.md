# Post-processing Tab

It loads completed job data (`collection.mat`), allows researchers to adjust outlier filters, inspect individual trajectories, and perform iOC calibration.

---

## Technical Workflows

### 1. Outlier Filtering
Raw molecular trajectories contain noise or artifacts (such as dust or aggregated particles) that can skew the final physical conclusions. 
*   Researchers select which physical property to filter on (e.g., `N`, `iOC`, `D`, or `velocity`).
*   They choose standard deviation thresholds (e.g., `mean ± 3 * STD`) or custom numeric limits.
*   The system calls `matlab_bridge.find_outliers` to compute a boolean keep/discard mask and renders interactive scatter plots using **Plotly**.

### 2. Trajectory Preview
Users can click points in the scatter plot or choose specific indices to display raw position vs. frame trajectories for individual molecules, ensuring data validity.

### 3. iOC Calibration
Interferometric Scattering Microscopy detects signal contrast ($iOC$). To map these values to actual molecular weights or refractive indices, a calibration is required:
*   A polynomial or linear regression calibration curve is fitted to the data.
*   Once calculated, values are updated in the data structures in-memory, and the resulting calibrated dataset can be downloaded.

---

## Code Reference

::: postprocessing

<details>
<summary>Source Code</summary>

```python
--8<-- "streamlit/postprocessing.py"
```

</details>

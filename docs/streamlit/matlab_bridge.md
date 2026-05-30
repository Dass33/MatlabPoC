# MATLAB Bridge

Interface to the compiled MATLAB algorithm via JSON serialisation.

MCR is initialised once per process on first call. All functions communicate via JSON strings so no MATLAB-specific Python types leak into the rest of the codebase.

<details>
<summary>Source</summary>

```matlab
--8<-- "matlab/nsm-data-analysis/runIocCalibration.m"
```

</details>


## Outlier Filtering
<details>
<summary>Source</summary>

```matlab
--8<-- "matlab/nsm-data-analysis/runOutlierFiltering.m"
```

</details>

## Population Analysis

<details>
<summary>Source</summary>

```matlab
--8<-- "matlab/nsm-data-analysis/runPopulationAnalysis.m"
```

</details>

## Postprocessing

<details>
<summary>Source</summary>

```matlab
--8<-- "matlab/nsm-data-analysis/runPostprocessing.m"
```

</details>

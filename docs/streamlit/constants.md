# Constants

Single source of truth for all default values and shared constants in the app.
This is the first place to look when tuning algorithm defaults or UI display settings.

## Algorithm defaults

`DEFAULT_CONFIG` — default values for all algorithm parameters submitted with each job.

## Outlier filtering defaults

`FILTER_DEFAULTS` — per-property default threshold direction and type (e.g. `iOC: both / 3std`).

`TV_OPTIONS` / `DIR_OPTIONS` — valid choices for threshold type and direction.

`SCALAR_PROPS` — ordered list of filterable scalar properties, derived from `FILTER_DEFAULTS`.

`MICRO_PROPS` — properties displayed in µ units (`iOC`, `STDiOC`).

## Population analysis

`AVAILABLE_PROPS` — properties shown in the Population Analysis tab.

## UI display

`STATES` — scatter plot marker colour and symbol per trajectory state (auto-kept, manual-excluded, …).

`TRACK_PALETTE` — colour cycle used in the track preview plot.

`STATUS_ICON` — emoji icons for job status labels used in the History tab.

<details>
<summary>Source</summary>

```python
--8<-- "streamlit/constants.py"
```

</details>

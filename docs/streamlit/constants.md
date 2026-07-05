# Constants Module

The `streamlit/constants.py` file exposes default parameters, labels, and ranges used across the user interface.

---

## Technical Purpose

Centralising constants prevents magic numbers from spreading throughout individual tab modules, facilitating global configuration tweaks (e.g. updating default filter properties or standard ranges).
(Note that currently there still are some magic numbers, especially in postprocessing.py)

---

## Code Reference

::: core.postprocessing

<details>
<summary>Source Code</summary>

```python
--8<-- "streamlit/constants.py"
```

</details>

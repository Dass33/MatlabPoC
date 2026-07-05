# MATLAB Bridge

The **MATLAB Bridge** (`streamlit/matlab_bridge.py`) serves as the programmatic interface between Python and the compiled MATLAB functions for outlier filtering, post-processing, and population analysis.

---

## Technical Details

### 1. In-Memory Initialization
The Python module wraps the custom compiled `nsm_algorithms` library. The MATLAB Runtime (MCR) is initialized once per process on the first call using `nsm_algorithms.initialize()`.

### 2. JSON Serialization
The bridge serialises all parameters to JSON string format before passing them to MATLAB. The MATLAB functions process the JSON payload, execute the mathematical routines, and return a JSON string, which is then parsed back into standard NumPy arrays and dictionaries in Python.

---

## Code Reference

::: connectors.algorithms

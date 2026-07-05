# Job Manager

The **Job Manager** (`streamlit/job_manager.py`) is a core component. It coordinates the lifecycle of background MATLAB analyses.

---

## Technical Details

### 1. Job Directory Layout
The manager organizes job variables in the filesystem:
```text
data/jobs/
└── <job_uuid>/
    ├── meta.json         # Stores user metadata (name, date, status)
    ├── input/            # Raw TIFF and TXT configuration files
    └── output/           # Compiled results, kymographs, status.json
```

### 2. Spawning MATLAB Subprocesses
To process a job, the manager:
1. Spawns `run_AnalyzeExperimentApp.sh` as an independent subprocess using Python's `subprocess.Popen`.
2. Passes parameters like input paths, output paths, and calibration settings.
3. Sets environment paths (`LD_LIBRARY_PATH`) so the executable runs against the MATLAB Runtime (MCR).

### 3. Background Thread Reaping
*   A daemon thread (`_process_reaper`) is spawned for each job.
*   The thread polls for status, waits for the process to exit, and writes exit codes or execution errors to `output/status.json`.

---

## Code Reference

::: connectors.storage

::: connectors.launcher

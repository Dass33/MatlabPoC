# Overview & Admin Tab

The system does not use a SQL database (relying on structured folder schemas in the filesystem instead), this module manages job folders.

---

## Core Features

### 1. Job Directory Scan
The page scans the `data/jobs/` directory, loading the `meta.json` file for each job. It lists:
*   Experiment Label / Name
*   Unique Job UUID
*   Submission Time
*   Files (input TIFF names)
*   "Kept" — n_kept/n_total trajectories from post-processing
*   "iOC µ (mean)" — the population's mean iOC (×1e6), once population analysis has run
*   Current Status (`processing`, `completed`, `failed`, `unknown`)

### 2. Download ZIP Archive
Users can compile and download a ZIP file containing the outputs of a completed run:
*   `config.json` and `Setting.json` — the parameters used for the run.
*   `kymographs/*.png` — kymograph previews.
*   `collection/collection.mat` — the raw MATLAB trajectory collection.
*   `collection_postprocessed.json` and `population.json`.
*   `trajectories.csv` — per-trajectory scalar properties, Excel/Origin-friendly.
*   `collection_postprocessed.mat` — the curated collection as a MATLAB struct.
*   `report.html` — a self-contained summary report.

### 3. Clone & Re-run
Users can re-analyze a completed job's input files under a new job, optionally reusing its
original config or the current sidebar config — useful for re-running with tweaked parameters
without re-uploading files.

### 4. Stuck Jobs
If a system reboot or an unexpected hardware crash occurs during a job execution, the status remains marked as `processing`.
*   The tab includes an administrator expander.
*   Admins can select a stuck job and mark it as "failed" manually. This writes a `status.json` with an error message and frees up the queue.

---

## Code Reference

::: tabs.overview

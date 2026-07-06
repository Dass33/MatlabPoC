# Overview & Admin Tab

The system does not use a SQL database (relying on structured folder schemas in the filesystem instead), this module manages job folders.

---

## Core Features

### 1. Job Directory Scan
The page scans the `data/jobs/` directory, loading the `meta.json` file for each job. It lists:
*   Experiment Label / Name
*   Unique Job UUID
*   Submission Time
*   Current Status (`processing`, `completed`, `failed`, `unknown`)

### 2. Download ZIP Archive
Users can compile and download a ZIP file containing the full outputs of a completed run:
*   TIFFs and metadata.
*   PNG previews of kymographs.
*   Matlab saves (`collection/collection.mat`).
*   Post-processed dataset JSON and population figures.

### 3. Stuck Jobs
If a system reboot or an unexpected hardware crash occurs during a job execution, the status remains marked as `processing`.
*   The tab includes an administrator expander.
*   Admins can select a stuck job and mark it as "failed" manually. This writes a `status.json` with an error message and frees up the queue.

---

## Code Reference

::: tabs.overview

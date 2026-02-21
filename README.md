# NSM Data Processing

Web application for processing Nanofluidic Scattering Microscopy (NSM) data.
A small team of scientists (4–6 users) upload raw kymograph TIFF files,
configure algorithm parameters, and retrieve results. The heavy computation
is done in MATLAB; the frontend is Streamlit.

## Repository Structure

```
/
├── streamlit/
│   ├── main.py              # Entire Streamlit frontend (single file)
│   ├── requirements.txt
│   └── Dockerfile
├── matlab/
│   ├── matlab_src/
│   │   ├── analyze_image.m  # Main entry point (compiled into the container)
│   │   └── ...              # Algorithm implementation (kymographAnalysis/, Utils/, etc.)
│   ├── Compiled/            # Pre-compiled MATLAB binary + support files
│   └── Dockerfile
├── data/                    # Job data (gitignored), mounted as Docker volume
├── docker-compose.yml
├── .env                     # HOST_DATA_DIR (required, not committed)
└── scripts/
    ├── compile_matlab.sh    # Compile analyze_image.m via mcc
    ├── build_matlab.sh      # Build the MATLAB Docker image
    ├── build_streamlit.sh   # Build the Streamlit Docker image
    └── deploy.sh            # Compile → build → docker compose up
```

## Two-Container Design

### Streamlit container

- Runs continuously, serves the UI on port 8501.
- Has access to the Docker socket (`/var/run/docker.sock`) so it can
  spawn MATLAB containers on demand.
- Reads/writes job data via a shared Docker volume (`data`).

### MATLAB container

- Spawned per job by Streamlit via the Docker Python SDK (`detach=True, remove=True`).
- Runs the compiled `analyze_image` binary, exits when done.
- Never kept running between jobs.

## Job Lifecycle

```
/data/jobs/{job_id}/
    config.json     ← written by Streamlit before container launch
    meta.json       ← job metadata (id, filenames, timestamp)
    input/          ← TIFF files, streamed to disk in 8 MB chunks (not buffered in RAM)
    output/
        status.json ← owned by MATLAB: processing → completed | failed
        *.mat       ← one result file per input TIFF
```

1. User uploads TIFFs and configures parameters in the Streamlit sidebar.
2. Streamlit streams files to `input/`, writes `config.json` and `meta.json`,
   launches the MATLAB container.
3. MATLAB container mounts the job root at `/job`, reads `/job/config.json`,
   processes all TIFFs in `/job/input/`, writes `.mat` results and `status.json`
   to `/job/output/`.
4. Streamlit polls `status.json` every N seconds (configurable via `POLL_INTERVAL_S`).
5. On completion, results are loaded from `.mat` files and displayed.

## Slot Management

- `MAX_WORKERS=2` concurrent MATLAB containers allowed (env var).
- Streamlit counts jobs where `status == "processing"` to determine free slots.
- If no slots are free, the Submit button is disabled.
- Users can choose to wait actively (auto-polling spinner) or submit and return
  to the History tab later.
- All users share the same job history (filesystem-based, not session-based).

## Config / Defaults

- **All parameter defaults live exclusively in Streamlit** (`DEFAULT_CONFIG` dict in `main.py`).
- Streamlit always writes the full config to `config.json` (no partial configs).
- MATLAB reads `config.json` via `jsondecode` and has **no defaults of its own**.
- Users can export/import config as JSON via the sidebar.
- The `arguments` block in `analyze_image.m` documents parameter types only,
  not defaults.

## MATLAB Entry Point (`analyze_image.m`)

Signature: `analyze_image(inputDir, outputDir)`

Pipeline inside `process_single_tiff`:

1. Preprocessing
2. Denoising
3. Detection
4. Contrast image
5. Position refinement
6. Contrast extraction
7. Tracking / linking → `FinalTracks`

Saves per TIFF: `FinalTracks`, `Detections`, `Y` (denoised), `C` (contrast) as `-v7.3` MAT file.

`write_status()` uses atomic write (temp file + rename) so Streamlit never
reads a half-written JSON. Per-file errors are collected from `parfor` and
aggregated; partial success (some files ok, some failed) is reported as `failed`
with a pipe-separated error string.

## Environment Variables

Configured in `docker-compose.yml` / `.env`:

| Variable         | Default                  | Purpose                              |
|------------------|--------------------------|--------------------------------------|
| `DATA_DIR`       | `/data/jobs`             | Base path for job directories        |
| `HOST_DATA_DIR`  | *(required in `.env`)*   | Same path as seen by the host daemon |
| `MATLAB_IMAGE`   | `matlab-algorithm:latest`| Docker image name for MATLAB container |
| `MAX_WORKERS`    | `2`                      | Max concurrent MATLAB containers     |
| `POLL_INTERVAL_S`| `5`                      | Seconds between status.json polls    |

## How to Run

### Prerequisites

- Docker and Docker Compose
- MATLAB (only needed to recompile `analyze_image.m`; not needed at runtime)

### Quick Start

1. Copy `.env` and set `HOST_DATA_DIR` to the absolute path of the `data/` directory on your host:
   ```bash
   # .env
   HOST_DATA_DIR=/absolute/path/to/MatlabPoC/data
   ```

2. Build and start:
   ```bash
   ./scripts/deploy.sh
   ```
   This compiles the MATLAB source, builds both Docker images, and starts
   the stack via `docker compose up -d`.

3. Open http://localhost:8501.

### Individual Build Steps

```bash
# Compile MATLAB source (requires MATLAB on PATH)
./scripts/compile_matlab.sh

# Build MATLAB Docker image only
./scripts/build_matlab.sh

# Build Streamlit Docker image only
./scripts/build_streamlit.sh
```

## Future: Cluster Migration (Golias / HTCondor)

The Golias farm at FZU uses HTCondor with native Docker universe support.
When the time comes, the only change needed is to replace `launch_matlab_container()`
in `main.py` with a `submit_htcondor_job()` function that writes an HTCondor
submit file and calls `condor_submit` via subprocess. Everything else —
job directory layout, config.json, status.json, results display — stays unchanged,
provided the `data/jobs/` directory lives on NFS visible to both the submit
node and worker nodes.

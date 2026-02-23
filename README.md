# NSM Data Processing

Web application for processing Nanofluidic Scattering Microscopy (NSM) data.
A small team of scientists upload raw kymograph TIFF files (+ paired `.txt` metadata),
configure algorithm parameters, and retrieve results. The heavy computation is done in
MATLAB; the "frontend" is in Streamlit.

## Repository Structure

```
/
├── streamlit/
│   ├── main.py              # App entry point, routing, job submission UI
│   ├── config.py            # DEFAULT_CONFIG, _build_config, sidebar widgets
│   ├── job_manager.py       # Job dirs, status polling, Docker launch
│   ├── results.py           # load_summary, load_trajectories, result rendering
│   ├── requirements.txt
│   └── Dockerfile
├── matlab/
│   ├── matlab_src/
│   │   ├── AnalyzeExperimentApp.m   # App entry point
│   │   ├── AnalyzeExperiment.m      # Original script (used for reference)
│   │   └── ...                      # Algorithm implementation (kymographAnalysis/, Utils/, etc.)
│   ├── Compiled/            # Pre-compiled MATLAB binary (gitignored, produced by compile_matlab.sh)
│   └── Dockerfile
├── tests/
│   ├── conftest.py          # Shared fixtures, mocks, CLI options
│   ├── unit/                # Fast tests — no Docker, no MATLAB
│   ├── integration/         # Full pipeline test against matlab-algorithm:latest
│   └── fixtures/            # Synthetic TIFF+TXT input, golden reference values
├── data/                    # Job data (gitignored), mounted as Docker volume
├── docker-compose.yml
├── pyproject.toml           # pytest configuration
├── requirements-test.txt    # Test dependencies
├── .env                     # HOST_DATA_DIR (required)
└── scripts/
    ├── compile_matlab.sh    # Compile AnalyzeExperimentApp.m via mcc
    ├── build_matlab.sh      # Build the MATLAB Docker image
    └── deploy_prod.sh       # rsync → restart stack on production server
```

## Two-Container Design

### Streamlit container

- Runs continuously, serves the UI on port 8501.
- Has access to the Docker socket (`/var/run/docker.sock`) so it can spawn MATLAB containers on demand.
- Reads/writes job data via a shared Docker volume (`data/`).

### MATLAB container

- Spawned per job by Streamlit via the Docker Python SDK (`detach=True, remove=True`).
- Runs the compiled `AnalyzeExperimentApp` binary, exits when done.
- Never kept running between jobs.

## Job Lifecycle

```
/data/jobs/{job_id}/
    config.json     ← written by Streamlit before container launch
    meta.json       ← job metadata (id, filenames, timestamp)
    input/          ← TIFF files + paired .txt metadata files
    output/
        status.json         ← owned by MATLAB: processing → completed | failed
        kymographs/*.png    ← kymograph images with track overlays
        trajectories.mat    ← per-trajectory scalars (scipy v7 compatible)
        summary.json        ← population statistics per sweep
        results.mat         ← full archive for MATLAB post-processing (v7.3)
```

1. User uploads `.tiff` files and their paired `.txt` metadata files, configures parameters.
2. Streamlit streams files to `input/`, writes `config.json` and `meta.json`, launches the MATLAB container.
3. MATLAB container mounts the job root at `/job`, reads `/job/config.json`, processes all TIFFs in `/job/input/`, writes results and `status.json` to `/job/output/`.
4. Streamlit polls `status.json` every N seconds (configurable via `POLL_INTERVAL_S`).
5. On completion, results are displayed: kymograph images, trajectory scatter plots, population metrics.

## Input File Format

The `tiff2` format pairs each `.tiff` with a same-name `.txt`
metadata file containing acquisition parameters (frame count, dimensions, exposure time, etc.).
**Both files must be uploaded together.** The app accepts `.tif`, `.tiff`, and `.txt`.

## MATLAB Pipeline (`AnalyzeExperimentApp.m`)

Signature: `AnalyzeExperimentApp(inputDir, outputDir)`

```
config.json → build_setting() → Setting struct
                                      │
                            kymographAnalysis(inputDir, Setting)
                                      │  produces kymographs/*.png
                                      ▼
                                 collection[]
                                      │
                            trajectoryAnalysis (positionStart, positionEnd)
                                      │
                            collectionPostprocessing  → outlier filtering + iOC calibration
                                      │
                            analyzePopulation_robustMean / GMM
                                      │
                            save_trajectories()  → trajectories.mat
                            save_summary()       → summary.json
                            save()               → results.mat
```

The pipeline mirrors `AnalyzeExperiment.m` (the researcher's original script). That file is the
authoritative reference — when the researcher updates it, `AnalyzeExperimentApp.m` must be
updated to match.

**Key constraint:** `positionStart` and `positionEnd` must NOT be included in
`Setting.kymographAnalysis.trajectoryProperties`. They are always computed via explicit
`trajectoryAnalysis` calls after `kymographAnalysis` returns, matching `AnalyzeExperiment.m`.

## Slot Management

- `MAX_WORKERS=2` concurrent MATLAB containers allowed (env var).
- Streamlit counts jobs where `status == "processing"` to determine free slots.
- If no slots are free, the Submit button is disabled.
- Users can wait actively (auto-polling spinner) or submit and return to History later.
- All users share the same job history (filesystem-based, not session-based).

## Config / Defaults

- **All parameter defaults live in Streamlit** (`DEFAULT_CONFIG` dict in `streamlit/config.py`).
- Streamlit writes the full config to `config.json` (no partial configs).
- MATLAB reads `config.json` via `jsondecode` and has no defaults of its own.
- Users can export/import config as JSON via the sidebar.
- Adding a new parameter requires changes in three places: `DEFAULT_CONFIG`, the sidebar widget, and `build_setting()` in `AnalyzeExperimentApp.m`.

## Environment Variables

Configured in `docker-compose.yml` / `.env`:

| Variable          | Default                   | Purpose                                |
|-------------------|---------------------------|----------------------------------------|
| `DATA_DIR`        | `/data/jobs`              | Base path for job directories          |
| `HOST_DATA_DIR`   | *(required in `.env`)*    | Same path as seen by the Docker daemon |
| `MATLAB_IMAGE`    | `matlab-algorithm:latest` | Docker image name for MATLAB container |
| `MAX_WORKERS`     | `2`                       | Max concurrent MATLAB containers       |
| `POLL_INTERVAL_S` | `5`                       | Seconds between status.json polls      |

## How to Run

### Prerequisites

- Docker and Docker Compose
- MATLAB R2025b (only needed to recompile; not needed at runtime)

### Quick Start

1. Set `HOST_DATA_DIR` in `.env` to the absolute path of the `data/` directory on your host:
   ```
   HOST_DATA_DIR=/absolute/path/to/MatlabPoC/data
   ```

2. Build and start:
   ```bash
   ./scripts/deploy.sh
   ```
   This compiles the MATLAB source, builds both Docker images, and starts the stack.

3. Open http://localhost:8501

### Updating Only the Streamlit Frontend

```bash
docker compose up --build -d
```

### Updating the MATLAB Algorithm

```bash
./scripts/compile_matlab.sh   # requires MATLAB on PATH
./scripts/build_matlab.sh     # rebuilds matlab-algorithm:latest
docker compose up -d
```

## Testing

### Unit tests (no Docker, no MATLAB required)

```bash
python -m venv .venv-test
source .venv-test/bin/activate
pip install -r requirements-test.txt
pytest tests/unit/
```

### Integration test (requires `matlab-algorithm:latest` image)

```bash
pytest tests/integration/ --run-integration
```

First run — establish golden reference values:
```bash
pytest tests/integration/ --run-integration --update-golden
```

Subsequent runs — catch regressions against the baseline:
```bash
pytest tests/integration/ --run-integration --check-golden
```

See `tests/fixtures/golden/README.md` for details on tolerance levels and regenerating fixtures.

## Known Issues

- **`struct([])` pre-initialization** — `TwoPassKymographProcessing.m`, `trackFiltering.m`, and `showKymograph.m` use `PARTICLES = struct([])` / `FinalTracks = struct([])` before loop assignments. Per MATLAB semantics, this causes a *"Subscripted assignment between dissimilar structures"* error if the struct gains new fields mid-loop. Workaround: remove the pre-init line (let MATLAB create the variable on first assignment).

## Future: Cluster Migration (Golias / HTCondor)

The Golias farm at FZU uses HTCondor with native Docker universe support.
When the time comes, the only change needed is to replace `launch_matlab_container()`
in `main.py` with a `submit_htcondor_job()` function that writes an HTCondor submit file
and calls `condor_submit` via subprocess. Everything else — job directory layout,
`config.json`, `status.json`, results display — stays unchanged, provided `data/jobs/`
lives on NFS visible to both submit node and worker nodes.

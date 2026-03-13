# NSM Data Processing

Web application for processing Nanofluidic Scattering Microscopy (NSM) data.
Upload raw kymograph TIFF files (+ paired `.txt` metadata),
configure algorithm parameters, and retrieve results. The heavy computation is done in
MATLAB; the "frontend" is in Streamlit.

## Repository Structure



## Two-Container Design

### Streamlit container

- Runs continuously, serves the UI on port 8501.
- Can spawn MATLAB containers on demand.
- Reads/writes job data via a shared Docker volume.

### MATLAB container

- Spawned per job by Streamlit via the Docker Python SDK.
- Runs the compiled `AnalyzeExperimentApp` binary, exits when done.
  
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

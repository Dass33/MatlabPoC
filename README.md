# NSM Data Processing

Web application for processing Nanofluidic Scattering Microscopy (NSM) data.
Upload raw kymograph TIFF files (+ paired `.txt` metadata),
configure algorithm parameters, and retrieve results. The heavy computation is done in
MATLAB; the "frontend" is in Streamlit.

For more detail check out the documentation available [here](https://dass33.github.io/MatlabPoC/).

## Architecture

A single Docker container serves the Streamlit UI and runs the compiled `AnalyzeExperimentApp`
binary as a subprocess for each submitted job. Job data is stored in the mounted `data/` volume.

## How to Run

### Prerequisites

- Docker and Docker Compose
- MATLAB R2025b (only needed to recompile; not needed at runtime)

### Local Development

1. Build and start:
   ```bash
   ./scripts/start.sh
   ```
   This compiles the MATLAB source, builds the Docker image, and starts the stack.

2. Open http://localhost:8501

### Production Deployment

Push image to Docker registry (Watchtower will auto-update):
```bash
./scripts/deploy.sh
```

Changes will be deployed within 5 minutes via Watchtower.

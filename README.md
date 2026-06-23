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

### Setup and Prerequisites

- Docker and Docker Compose
- Python 3

Before running or developing, run the cross-platform setup script to initialize/update git submodules, copy configuration templates, create the python virtual environment, install requirements, and clean up obsolete residues:

```bash
python scripts/setup.py
```

MATLAB R2025b is only needed to recompile the binary; it is not required at runtime.

### Running locally

```bash
docker compose up
```

Open http://localhost:8501.

### Deploying

Build and push to Docker Hub (Watchtower on the production machine picks it up within ~5 minutes):

```bash
python scripts/deploy.py
```

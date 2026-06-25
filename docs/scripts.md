# Developer Scripts

This project includes a set of Python helper scripts in the `scripts/` directory to automate common development, building, compilation, and deployment tasks.

## Quick Reference Table

| Script Name | Purpose | Command |
| :--- | :--- | :--- |
| `setup.py` | Initial repository setup, submodules update, virtual environment, and dependency installation. | `python scripts/setup.py` |
| `run_streamlit.py` | Runs the Streamlit web application locally in development mode. | `python scripts/run_streamlit.py` |
| `compile_matlab.py` | Compiles MATLAB source code into a standalone binary and a Python package. | `python scripts/compile_matlab.py` |
| `build_streamlit.py` | Builds and tags the local Streamlit Docker image. | `python scripts/build_streamlit.py` |
| `start.py` | Performs compilation, builds the Docker image, and restarts the docker-compose stack. | `python scripts/start.py` |
| `deploy.py` | Builds and pushes the production Docker image to Docker Hub. | `python scripts/deploy.py` |

---

## Detailed Script Descriptions

### setup.py
* **When to run**: Run this once after cloning the repository, or when dependencies change.
* **Key Tasks**:
    1. Initializes and updates git submodules recursively.
    2. Copies `.env.example` to `.env` if not already present.
    3. Creates a Python virtual environment in `streamlit/venv`.
    4. Installs Python dependencies from `streamlit/requirements.txt` and `requirements-dev.txt`.

### run_streamlit.py
* **When to run**: Run this to launch the Streamlit frontend locally without Docker.
* **Key Tasks**:
    1. Loads environment variables from `.env`.
    2. Launches the Streamlit app using the virtual environment's executable.

### compile_matlab.py
* **When to run**: Run this when modifying the MATLAB code under `matlab/`.
* **Prerequisites**: Requires MATLAB R2025b with the `mcc` compiler installed and available in the system PATH.
* **Key Tasks**:
    1. Compiles the standalone analysis application to `matlab/Compiled/AnalyzeExperimentApp`.
    2. Generates the Python package bridge `nsm_algorithms` in `matlab/Compiled/PythonPackage/`.

### build_streamlit.py
* **When to run**: Run this to build the local Streamlit Docker image.
* **Prerequisites**: Docker daemon running.
* **Key Tasks**:
    1. Builds the Docker image locally from `streamlit/Dockerfile`.
    2. Tags the image as `dass33/nsm-streamlit:latest`.

### start.py
* **When to run**: Run this to perform a full local rebuild and container restart.
* **Prerequisites**: MATLAB (for compilation) and Docker/Docker Compose installed.
* **Key Tasks**:
    1. Compiles the latest MATLAB code (`compile_matlab.py`).
    2. Builds the latest Streamlit Docker image (`build_streamlit.py`).
    3. Restarts the docker-compose services using `docker compose down` and `docker compose up -d`.

### deploy.py
* **When to run**: Run this to publish a new release to Docker Hub.
* **Prerequisites**: Docker daemon running and push permissions to the `dass33/nsm-streamlit` repository.
* **Key Tasks**:
    1. Builds the Docker image.
    2. Pushes the image to Docker Hub, where Watchtower will automatically deploy it on the production server.

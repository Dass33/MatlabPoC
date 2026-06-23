# Deployment Guide

The NSM Web Application is containerised with Docker to make deployments predictable and portable. It can run on premise and on cloud hosting providers ([VPS](https://en.wikipedia.org/wiki/Virtual_private_server), like [Hetzner](https://www.hetzner.com/)).

---

## 1. On-Premise Deployment

The primary production deployment runs on the lab's dedicated local server using Docker Desktop on Windows.

### Installation Steps
1. Install [Docker Desktop](https://docs.docker.com/desktop/) on the target host machine.
2. Clone the repository or download the package files to the server.
3. Configure the environment variables in `.env` (see below).
4. Run the Docker Compose stack in detached mode:
   ```bash
   docker compose up -d
   ```
5. The application will be serving HTTP requests at **`http://localhost:8501`**.

---

## 2. Docker Compose Configuration

The application stack consists of two services defined in `docker-compose.yml`:
1. **`streamlit`**: The core application serving the web interface and executing background MATLAB jobs.
2. **`watchtower`**: An automation utility that checks for updated container images and restarts the stack seamlessly.

### Environment variables

Customize runtime configurations by editing the `.env` file at the project root:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `DATA_DIR` | Folder path inside container where job data is written. | `/data/jobs` |
| `POLL_INTERVAL_S` | Tick rate (seconds) at which Streamlit polls for status updates. | `5` |
| `MATLAB_APP` | Path to the compiled executable shell runner script. | `/opt/matlab_app/run_AnalyzeExperimentApp.sh` |

### Volumes & Port Mapping

*   **Port `8501:8501`**: Map the internal Streamlit web server port to the host server.
*   **Volume `./data:/data/jobs`**: Mounts a local database directory (`data/`) on the host machine to the container's internal data directory. This ensures raw TIFF files and output JSON results persist across container updates and restarts.

---

## 3. Continuous Deployment with Watchtower

The production container is kept up-to-date automatically:
1. When developers run `python scripts/deploy.py`, a new production-ready image is built and pushed to the Docker Hub repository (`dass33/nsm-streamlit:latest`).
2. The `watchtower` service on the deployment server queries the Docker Hub registry every 5 minutes (300 seconds).
3. If a new image digest is found, Watchtower pulls the latest container image, cleanly stops the existing `streamlit` container, and boots a new one with identical environment configurations. No manual SSH or intervention is required.

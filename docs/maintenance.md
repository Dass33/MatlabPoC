# Maintenance

For the app to be usable long term it has to be maintained. This page offers knowledge from the authors to make it easier for a new maintainer to start.

## Setting up project
To set up the workspace for development, run the setup script:

```bash
python scripts/setup.py
```

To run the app you only need [Docker](https://docs.docker.com/compose/). [Docker Desktop](https://docs.docker.com/desktop/) is a user-friendly option and is what the current Windows deployment uses.

To build and deploy changes you also need Docker and push access to the Docker Hub repo. Recompiling the MATLAB binary additionally requires MATLAB R2025b.

```bash
python scripts/deploy.py   # build the Docker image and push it to Docker Hub
```

Watchtower on the production machine will pick up the new image automatically within ~5 minutes — no action needed there.

To start the full stack locally (build + run):

```bash
docker compose up --build
```

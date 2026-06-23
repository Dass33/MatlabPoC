# Deployment

Currently the app is deployed on premise, but it supports deployments in several other environemnts notably on virtual private server, cloud run, or with small modifications on a cluster.

## On premise (current deployment)

### How to deploy locally (windows)

1. Install [Docker Desktop](https://docs.docker.com/desktop/) and make sure it is running.
2. Start the stack:
   ```bash
   docker compose up -d
   ```
3. Open `http://localhost:8501`.

Updates are deployed by pushing new images from the development machine — Watchtower picks them up automatically within ~5 minutes, no action needed on the Windows machine.

## Deploying to VPS
The app was deployed in the past to Hetzner VPS, which is great solution for the ease of setup, reliable monthly fee, and reliability.
The downsides are the presence of monthly fee and the fact that the lab is in possesion of strong hardware that can be utilized for the task.


## Deploying to cluster
Even though it is slightly trickier to pull off it could have great benefits, if the researchers need to scale the experiments up.
For deploying to cluster there would have to be some changes made, but the architecture overall supports is well.

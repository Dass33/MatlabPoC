# NSM Web App

It's a web application which serves as an easy to use intefrace to operate the NSM algorithm to analyze epxeriments.

## Architecture
The app consists of two main parts, the web app made with Streamlit and the Matalb algorithm which is present as [Git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) (we have other repo inserted into the project and can pull new commits to it), they are bundled together using [Docker compose](https://docs.docker.com/compose/), using docker also let's us deploy to almost any environemnt, with great ease.

Below is a flow chart which represent how the high level architecture of the app looks like.
```mermaid
flowchart TB
    User(["User"])

    subgraph StreamlitContainer["Streamlit Container (persistent)"]
        direction TB
        Streamlit["Streamlit App"]
        MCR1["MATLAB Runtime"]
        Streamlit -->|Post processing| MCR1
    end

    DataVol["Shared Volume"]

    subgraph MatlabContainer["MATLAB Container (per-job)"]
        direction TB
        AnalyzeApp["AnalyzeExperimentApp.m"]
        MCR2["MATLAB Runtime"]
        AnalyzeApp --> MCR2
    end

    DockerHub(["🐳 Docker Hub"])
    DockerHub -.->|pulls images| Watchtower

    User -->|Connects using browser| Streamlit
    Streamlit -->|Docker SDK| AnalyzeApp

    AnalyzeApp <-->|read/write JSON| DataVol
    Streamlit <-->|read/write JSON| DataVol

    Watchtower -.->|updates| StreamlitContainer
    Watchtower -.->|updates| MatlabContainer
    StreamlitContainer ~~~ MatlabContainer
```

### Streamlit container

- Runs continuously, serves the UI on port 8501.
- Spawns MATLAB containers on demand via the Docker Python SDK.
- Reads/writes job data via a shared Docker volume.

### MATLAB container

- Spawned per job, runs the compiled `AnalyzeExperimentApp` binary, exits when done.
- Does not require a MATLAB license — only the MATLAB Runtime (MCR).

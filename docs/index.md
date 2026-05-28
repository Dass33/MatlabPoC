# NSM Web App

It's a web application which serves as an easy to use intefrace to operate the NSM algorithm to analyze epxeriments.

## Architecture
The app consists of two main parts, the web app made with Streamlit and the Matalb algorithm which is present as [Git submodule](https://git-scm.com/book/en/v2/Git-Tools-Submodules) (we have other repo inserted into the project and can pull new commits to it), they are bundled together using [Docker compose](https://docs.docker.com/compose/), using docker also let's us deploy to almost any environemnt, with great ease.

Below is a flow chart which represent how the high level architecture of the app looks like.
```mermaid
flowchart TB
    User(["👤 User (Browser)"])

    subgraph StreamlitContainer["Streamlit Container (persistent)"]
        direction TB
        Streamlit["Streamlit App"]
        JM["Job Manager"]
        Bridge["Post-processing Bridge"]
        MCR1["MATLAB Runtime"]
        Bridge --> MCR1
        Streamlit --> JM
        Streamlit --> Bridge
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

    User -->|HTTP :8501| Streamlit
    JM -->|Docker SDK| AnalyzeApp

    JM <-->|read/write| DataVol
    AnalyzeApp <-->|read/write| DataVol
    Bridge <-->|JSON| DataVol

    Watchtower -.->|updates| StreamlitContainer
    Watchtower -.->|updates| MatlabContainer
    StreamlitContainer ~~~ MatlabContainer
```

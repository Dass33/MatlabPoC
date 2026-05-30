# Maitenece

For the app to be usable long term it has to be maintained, this site offers knowledge from authors of the app, to make it easier for new maintainer to start.

## Setting up project
To get the project running one only need to have [docker](https://docs.docker.com/compose/), for example there is [Docker desktop](https://docs.docker.com/desktop/) app which is very user friendly, and using which the app is currently deployed on Windows machine locally.

For maintaining the app one has to be able to also build the containers containing their changes. For Streamlit-only changes this only requires Docker. Recompiling the MATLAB binary requires MATLAB R2025b.

```bash
./scripts/deploy.sh            # full build: compile MATLAB + build both images + start stack
./scripts/push.sh              # push both images to Docker Hub
./scripts/push.sh --matlab     # push only the MATLAB image
./scripts/push.sh --streamlit  # push only the Streamlit image
```

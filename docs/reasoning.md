It may be quite helpful for maintainers and users of this app to know reasoning behind some architectural choices this app makes, this page contains just that.

!!! note
    This page has less of a documentation character to get more concreate information about the interals of the app visit the appropriate pages from the sidebar.

The main goal is to make the app very accesible to researchers, keep the app simple and easy to maintain.
To fullfill these goals there were made some tradeoffs, bellow is written down the reasoning and architecture decisions for this app.


## Reusing the Matlab code
Creating new version of the algorithm, is quite a big task and maintaing two version of the algorithm has quite a big costs,
so it was decided that the Matlab code should be reused.
Being somewhat locked in Matlab ecosystem has some noticible downsides, like lower compatibility with other tools or licensing costs.

## Choosing Streamlit

Streamlit lets you build nice web apps in plain Python with no frontend development experience required, and is also very fast to do so.
The main tradeoff is that Streamlit is highly opionated and creating custom components is bit harder and every interaction triggers a full Python rerun, which can be done quite cheaply by having certain data cached in `st.session_state` and using `@st.cache_data` for file reads.

## Deployment decisions

On-premise deployment on the lab's existing hardware avoids a recurring cost and takes advantage of hardware that is already available.
Docker makes the setup portable as the containers can run on Windows locally, VPS, or a cluster with minimal changes.
Watchtower (container monitoring pushed continers to [Docker hub](https://hub.docker.com/)) removes the need for manual updating on the production machine when deploying updates.
(it is neccessary to config the correct Docker hub repo to monitor)


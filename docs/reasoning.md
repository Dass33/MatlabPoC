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

## Deployment decisions


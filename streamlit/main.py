import streamlit as st
import SimPackage


@st.cache_resource
def start_runtime():
    return SimPackage.initialize()


def main():
    matlab_algo_lib = start_runtime()
    st.title("hi")
    return


if __name__ == "__main__":
    main()

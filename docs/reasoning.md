# Architectural Decisions & Rationale

This document tracks major design choices made throughout the development of the NSM Data Processing application, including their associated trade-offs.

---

## 1. Reusing the Matlab Code

*   **Decision**: Reuse the existing MATLAB algorithms directly via compilation, rather than rewriting them in Python/C++.
*   **Rationale**: The algorithm is complex and changes frequently. Maintaining dual implementations (one in MATLAB for research and one in another language for production) would double development overhead and risk code drift.
*   **Trade-off**: Spawning a MATLAB compiled binary requires the MATLAB Runtime (MCR) to be installed, which makes Docker image size about 10GB and introduces startup latency. However, it requires no runtime license fees.

---

## 2. Choosing Streamlit for the Web UI

*   **Decision**: Implement the user interface as a single-page Streamlit Python application.
*   **Rationale**: Streamlit makes it very easy and fast to create dashboard interfaces and is very friendly to newcomers to web dev.
*   **Trade-off**: Streamlit is heavily opinionated, and doing custom components in it requires more effort.

---

## 3. Using docker

*   **Decision**: TODO
*   **Rationale**: TODO
    **Trade-off**: TODO

## 4. Using file system instead of DB

*   **Decision**: TODO
*   **Rationale**: TODO
    **Trade-off**: TODO

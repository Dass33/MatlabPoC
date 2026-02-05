# Refactoring & Workflow Plan

## Goal
Modularize the application for maintainability, optimize the Docker build process (especially MATLAB Runtime handling), and establish clear development guidelines.

## Phase 0: Baseline & DevOps Optimization
- [ ] **0.1 Versioning Baseline**: 
    - Fix `.gitignore` to properly exclude `SimPackage` artifacts and large binaries.
    - Commit current working state as a "baseline" using conventional commits.
- [ ] **0.2 Docker Runtime Optimization**:
    - Refactor `Dockerfile` to use a multi-stage build.
    - Stage 1: Install MATLAB Runtime (heavy, cached).
    - Stage 2: Install Python dependencies and Application code (light, fast).
    - *Goal*: Application changes should only trigger the light stage, making builds take seconds instead of minutes.

## Phase 1: Structure & Configuration
- [ ] **1.1 Scaffold**: Create `app/`, `tests/`, and `docs/` directories.
- [ ] **1.2 Dependencies**: Create `requirements.txt`.
- [ ] **1.3 Config Module**: Create `app/config.py`.
    - Move all sidebar inputs, default values, and JSON save/load logic here.

**Checkpoint**: Commit changes as `feat(arch): setup modular structure and config module`.

## Phase 2: Logic Modularization
- [ ] **2.1 Visualization**: Create `app/visualization.py`.
    - Move Matplotlib and results display logic.
- [ ] **2.2 Analysis**: Create `app/analysis.py`.
    - Move MATLAB initialization and execution wrapper.
- [ ] **2.3 Session State**: Create `app/session.py`.
    - Centralize `st.session_state` management and data aggregation.

**Checkpoint**: Commit changes as `refactor(logic): separate viz, analysis, and session logic`.

## Phase 3: Integration & Cleanup
- [ ] **3.1 Main Entry**: Create `app/main.py` (the new orchestrator).
- [ ] **3.2 Verification**: Run the app via `streamlit run app/main.py` and verify all features.
- [ ] **3.3 Cleanup**: Remove the monolithic `app.py`.
- [ ] **3.4 Documentation**: Update `README.md` with the new structure.

**Checkpoint**: Commit changes as `feat(app): finalize modular integration and remove monolith`.

## Phase 4: Quality & Guidelines
- [ ] **4.1 Style Check**: Ensure all new files follow `docs/AGENT_GUIDELINES.md`.
- [ ] **4.2 Basic Tests**: Add a few unit tests in `tests/` for the config and session logic.

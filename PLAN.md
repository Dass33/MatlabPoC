# Project Foundation & Automation Plan

## Phase 1: Code Quality & Tooling
- [x] **1.1 Tool Configuration**: 
    - Initialize `pyproject.toml` with configurations for `ruff` and `mypy`.
- [x] **1.2 Standardized Workflow**:
    - Create a `Makefile` with commands for linting, testing, and type checking.
- [x] **1.3 Mocking Strategy**:
    - Implement a mock for `SimPackage` and `matlab` for local/CI development.

## Phase 2: Hybrid MATLAB Workflow
- [x] **2.1 Sync & Build Script**:
    - Create `scripts/sync_and_build.py` to fetch MATLAB source, compile `mcc`, and build Python wheel.
- [x] **2.2 Binary Artifact Tracking**:
    - Set up `libs/` folder for `.whl` files and update `.gitignore`.
- [x] **2.3 Deployment Optimization**:
    - Update `Dockerfile` to install from the pre-built wheel, making CI builds fast and license-independent.

## Phase 3: CI/CD & Testing
- [x] **3.1 GitHub Actions**:
    - Automated `make check` on every push.
- [x] **3.2 Unit Tests**:
    - Coverage for Config, Session, and Visualization.
- [x] **3.3 Pre-commit Hooks**:
    - Set up `pre-commit` for local quality enforcement.
- [ ] **3.4 Integration Test**:
    - "Smoke test" for the Streamlit app logic.

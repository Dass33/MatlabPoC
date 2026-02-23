# Contributing Guide

## Prerequisites

| Tool | Purpose | Required always? |
|------|---------|-----------------|
| Docker + Docker Compose | Running the stack and integration tests | Yes |
| Python ≥ 3.10 | Unit tests, Streamlit dev | Yes |
| MATLAB R2025b + Image Processing + Curve Fitting toolboxes | Recompiling the algorithm | Only when changing MATLAB code |

## Running Tests

```bash
python -m venv .venv-test
source .venv-test/bin/activate   # or .venv-test\Scripts\activate on Windows
pip install -r requirements-test.txt
```

**Unit tests** (fast, no Docker needed):
```bash
pytest tests/unit/
```

**Integration test** (requires `matlab-algorithm:latest` to be built):
```bash
pytest tests/integration/ --run-integration
```

Always run unit tests before opening a PR. Integration tests should be run after any change to MATLAB source or `AnalyzeExperimentApp.m`.

## Changing the MATLAB Algorithm

The file `matlab/matlab_src/AnalyzeExperiment.m` is the researcher's authoritative script. **Do not modify it.** All changes go into `AnalyzeExperimentApp.m`, keeping it in sync with the researcher's script.

After editing `AnalyzeExperimentApp.m` or any file under `matlab/matlab_src/`:

```bash
./scripts/compile_matlab.sh   # produces matlab/Compiled/
./scripts/build_matlab.sh     # rebuilds matlab-algorithm:latest
pytest tests/integration/ --run-integration
```

If output values change intentionally (algorithm improvement), update the golden baseline:
```bash
pytest tests/integration/ --run-integration --update-golden
git add tests/fixtures/golden/reference.json
git commit -m "chore: update golden reference after <describe the change>"
```

### Key constraints to keep in mind

- `positionStart` and `positionEnd` must **not** appear in `Setting.kymographAnalysis.trajectoryProperties` — they are computed separately via explicit `trajectoryAnalysis` calls after `kymographAnalysis` returns.
- Do not pre-initialize struct arrays with `struct([])` before loop assignments — MATLAB raises *"Subscripted assignment between dissimilar structures"* if the struct gains new fields mid-loop. Let MATLAB create the variable on first assignment.
- `write_status` must use `jsonencode()` on a struct, not manual string building, to handle special characters correctly.

## Adding a New Algorithm Parameter

Three places must change together:

1. **`streamlit/config.py`** — add to `DEFAULT_CONFIG` and add a sidebar widget in `render_config_sidebar()`, then wire it through `_build_config()`.
2. **`streamlit/config.py` — `_build_config()`** — add the parameter to the function signature and assign it in the returned dict.
3. **`matlab/matlab_src/AnalyzeExperimentApp.m` — `build_setting()`** — read the new field from the `config` struct and assign it to the appropriate `Setting.*` field.

After adding a parameter, also update `validate_config()` in `AnalyzeExperimentApp.m` if the parameter is required (not optional with a sensible default).

Run `pytest tests/unit/test_config.py` to verify `DEFAULT_CONFIG` and `_build_config` still pass all checks.

## Changing Python / Streamlit Code

```bash
# Run the full unit suite after any Python change
pytest tests/unit/

# Locally test the UI (needs the MATLAB image already built)
docker compose up --build -d
# open http://localhost:8501
```

The Streamlit source is split into four modules:

| Module | Responsibility |
|--------|---------------|
| `main.py` | Page routing, file upload, job submission, history view |
| `config.py` | `DEFAULT_CONFIG`, sidebar parameter widgets, `_build_config` |
| `job_manager.py` | Job directory layout, status polling, Docker container launch |
| `results.py` | Loading output files, rendering plots and tables |

Keep these boundaries clean — `results.py` should not know about Docker, `job_manager.py` should not render UI, etc.

## Deploying to Production

Use the `/deploy` skill in Claude Code, or run the script directly:

```bash
./scripts/deploy_prod.sh                # Python/Streamlit changes only
./scripts/deploy_prod.sh --matlab       # Also rebuilt the MATLAB image on the server
```

The script rsyncs the project (excluding `.git/`, `.env`, `data/`) to `root@49.12.232.89:/opt/nsm-poc` and restarts the Docker stack. The server `.env` must have `HOST_DATA_DIR=/opt/nsm-poc/data`.

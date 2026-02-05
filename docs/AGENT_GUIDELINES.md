# Agent Development Guidelines

These guidelines are designed to ensure consistency, maintainability, and quality across the repository, especially when AI agents are performing modifications.

## 1. Code Style & Standards

### Python
- **Formatter**: Follow `ruff` formatting style.
- **Imports**: Organize imports: Standard Library -> Third Party -> Local Application.
- **Typing**: Use Python type hints (`from typing import ...`) for function arguments and return values.
- **Docstrings**: All public functions and classes must have docstrings (Google style or NumPy style preferred).
- **Variable Names**: Use `snake_case` for variables/functions and `PascalCase` for classes.

### MATLAB
- **Naming**: CamelCase (`myFunction`, `myVariable`) is standard in this project's existing code. Maintain consistency with surrounding files.
- **Comments**: Add `%` comments explaining complex logic steps.

## 2. Repository Structure
- **Source Code**: 
  - Python application code goes in `app/`.
  - MATLAB source code goes in `matlab_src/`.
- **Tests**: All tests go in `tests/`. Mirrored structure to source is preferred.
- **Configuration**: Hardcoded values should be moved to `app/config.py` or environment variables.

## 3. Git & Version Control
- **Commits**:
  - Format: `type(scope): description` (e.g., `feat(viz): add track length histogram`, `fix(parsing): handle empty CSVs`).
  - Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`.
- **Ignored Files**: Ensure large binaries (like `.ctf`, `.zip`) and build artifacts (`build/`, `dist/`, `__pycache__/`) are in `.gitignore`.
- **SimPackage**: The `SimPackage/` directory contains generated artifacts. Only the source configuration (like `setup.py` if customized manually) should be tracked if necessary, but generally, generated bindings should be treated as artifacts.

## 4. Error Handling
- **UI**: Use `st.error` for user-facing errors but always log the full traceback to the console/logs.
- **Graceful Failure**: The app should not crash on malformed input; catch exceptions and provide actionable feedback.

## 5. Testing
- **Unit Tests**: Write `pytest` compatible tests for utility functions.
- **Integration**: Verify the MATLAB-Python bridge functionality with small mock data if possible.

## 6. Documentation
- Update `README.md` when adding new features or changing installation steps.
- Keep architecture diagrams or descriptions up to date in `docs/`.

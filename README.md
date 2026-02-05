# NSM Data Processing App

A Streamlit-based application for processing NSM data using a MATLAB-based pipeline.

## Project Structure

```text
/
├── app/                        # Python application source
│   ├── main.py                 # Entry point (Streamlit app)
│   ├── analysis.py             # MATLAB interface wrapper
│   ├── config.py               # Sidebar & configuration management
│   ├── session.py              # Results & session state management
│   └── visualization.py        # Matplotlib rendering & results display
├── matlab_src/                 # MATLAB source code for the algorithm
├── tests/                      # Unit tests for Python logic
├── docs/                       # Guidelines & documentation
├── Dockerfile                  # Optimized multi-stage build
└── requirements.txt            # Python dependencies
```

## Getting Started

### Prerequisites
- MATLAB Runtime R2025b
- Python 3.10+

### Local Setup
1. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install the MATLAB-Python binding:
   ```bash
   cd SimPackage
   python -m pip install .
   ```
3. Run the application:
   ```bash
   export PYTHONPATH=$PYTHONPATH:.
   streamlit run app/main.py
   ```

### Running with Docker
The Dockerfile uses a multi-stage build to cache the MATLAB Runtime installation.
```bash
docker build -t nsm-app .
docker run -p 8501:8501 nsm-app
```

## Development

### Workflow & Automation
This project uses several tools to ensure code quality:
- **Ruff**: For extremely fast linting and formatting.
- **Mypy**: For static type checking.
- **Pytest**: For unit testing (with MATLAB mocks).

We use a `Makefile` to standardize these tasks:
- `make lint`: Run linting checks.
- `make format`: Auto-format code.
- `make typecheck`: Run static type analysis.
- `make test`: Run unit tests.
- `make check`: Run all of the above (recommended before pushing).

### CI/CD
A GitHub Action is configured to run `make check` on every push and pull request to the `main` branch.

### Pre-commit
To install pre-commit hooks:
```bash
pip install pre-commit
pre-commit install
```

Please refer to [docs/AGENT_GUIDELINES.md](docs/AGENT_GUIDELINES.md) for detailed coding standards.

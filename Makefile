.PHONY: install lint format typecheck test check sync-matlab help

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make lint          - Run ruff for linting"
	@echo "  make format        - Run ruff for formatting"
	@echo "  make typecheck     - Run mypy for type checking"
	@echo "  make test          - Run tests with pytest"
	@echo "  make check         - Run all checks (lint, format check, typecheck, test)"
	@echo "  make sync-matlab   - Sync from MATLAB repo and rebuild (Requires PATH_TO_MATLAB_REPO)"

install:
	pip install -r requirements.txt
	pip install ruff mypy pytest pytest-mock

lint:
	ruff check .

format:
	ruff format .

typecheck:
	mypy app/

test:
	export PYTHONPATH=. && pytest tests/

check: lint typecheck test
	@echo "All checks passed!"

sync-matlab:
	@if [ -z "$(PATH_TO_MATLAB_REPO)" ]; then echo "Error: PATH_TO_MATLAB_REPO is not set. Use: make sync-matlab PATH_TO_MATLAB_REPO=/path/to/repo"; exit 1; fi
	./scripts/sync_and_build.py $(PATH_TO_MATLAB_REPO) --push

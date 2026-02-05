.PHONY: install lint format typecheck test check help

help:
	@echo "Available commands:"
	@echo "  make install    - Install dependencies"
	@echo "  make lint       - Run ruff for linting"
	@echo "  make format     - Run ruff for formatting"
	@echo "  make typecheck  - Run mypy for type checking"
	@echo "  make test       - Run tests with pytest"
	@echo "  make check      - Run all checks (lint, format check, typecheck, test)"

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

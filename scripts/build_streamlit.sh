#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root resolved to: $PROJECT_ROOT"
cd "$PROJECT_ROOT"
cd ./streamlit
docker build -t matlabpoc-streamlit:latest .

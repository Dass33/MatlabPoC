#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

docker build -t dass33/nsm-streamlit:latest -f streamlit/Dockerfile .
docker push dass33/nsm-streamlit:latest

echo "Done. Watchtower will pick up changes within 5 minutes."

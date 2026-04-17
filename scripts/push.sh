#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

MATLAB_ONLY=false
STREAMLIT_ONLY=false

for arg in "$@"; do
  case $arg in
    --matlab) MATLAB_ONLY=true ;;
    --streamlit) STREAMLIT_ONLY=true ;;
  esac
done

if $MATLAB_ONLY; then
  docker build -t dass33/nsm-matlab:latest -f matlab/Dockerfile matlab/
  docker push dass33/nsm-matlab:latest
elif $STREAMLIT_ONLY; then
  docker build -t dass33/nsm-streamlit:latest -f streamlit/Dockerfile .
  docker push dass33/nsm-streamlit:latest
else
  docker build -t dass33/nsm-matlab:latest -f matlab/Dockerfile matlab/
  docker build -t dass33/nsm-streamlit:latest -f streamlit/Dockerfile .
  docker push dass33/nsm-matlab:latest && docker push dass33/nsm-streamlit:latest
fi

echo "Done. Watchtower will pick up changes within 5 minutes."

#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root resolved to: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

MATLAB_RUNTIME_PATH="/usr/local/MATLAB/R2025b/runtime/glnxa64"

if [ ! -d "$MATLAB_RUNTIME_PATH" ]; then
    echo "Error: MATLAB Runtime path not found at $MATLAB_RUNTIME_PATH"
    echo "Please verify your installation."
    exit 1
fi

echo "Setting up environment..."

if [ -f "./SimPackage/venv/bin/activate" ]; then
    source ./SimPackage/venv/bin/activate
elif [ -f "./SimPackage/venv/bin/activate.fish" ]; then
    echo "Warning: Using bash, but found .fish activation script. Attempting to source standard activate script if it exists."
fi

echo "Installing SimPackage..."
pushd SimPackage > /dev/null
pip install -e .
popd > /dev/null

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:"$MATLAB_RUNTIME_PATH"
echo "Starting Streamlit App..."
streamlit run app/main.py

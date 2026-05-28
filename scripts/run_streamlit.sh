#!/bin/bash
SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

source streamlit/venv/bin/activate
set -a # auto export variables to child process
source .env
set +a
streamlit run streamlit/main.py

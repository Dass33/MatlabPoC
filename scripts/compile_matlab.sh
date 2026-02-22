#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root resolved to: $PROJECT_ROOT"
cd "$PROJECT_ROOT"
cd ./matlab/Compiled
matlab -batch "mcc -m ../matlab_src/AnalyzeExperimentApp.m -a ../matlab_src/ -o AnalyzeExperimentApp"

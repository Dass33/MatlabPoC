#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root resolved to: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Used by the MATLAB Docker container for kymograph analysis
cd ./matlab/Compiled
matlab -batch "mcc -m ../nsm-data-analysis/AnalyzeExperimentApp.m -a ../nsm-data-analysis/ -o AnalyzeExperimentApp"
cd "$PROJECT_ROOT"

# Python package, used by the Streamlit bridge for postprocessing
mkdir -p ./matlab/Compiled/PythonPackage
cd ./matlab/Compiled/PythonPackage
matlab -batch "mcc -W python:nsm_algorithms \
    ../../nsm-data-analysis/runOutlierFiltering.m \
    ../../nsm-data-analysis/runIocCalibration.m \
    ../../nsm-data-analysis/runPostprocessing.m \
    ../../nsm-data-analysis/runPopulationAnalysis.m \
    -a ../../nsm-data-analysis/"

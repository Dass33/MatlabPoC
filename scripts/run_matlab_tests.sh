#!/usr/bin/env bash
# Run the MATLAB contract tests against the real compiled nsm_algorithms package.
#
# These are skipped by a plain `pytest` run because they need the MATLAB runtime
# on LD_LIBRARY_PATH. Point MCR_ROOT at a MATLAB or MATLAB Runtime R2025b install
# (defaults to the local full-MATLAB path) and this wires the loader paths up.
#
# Usage:  scripts/run_matlab_tests.sh            # just the integration tests
#         scripts/run_matlab_tests.sh -m ''      # whole suite incl. integration
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MCR_ROOT="${MCR_ROOT:-/usr/local/MATLAB/R2025b}"

if [[ ! -d "$MCR_ROOT" ]]; then
  echo "MATLAB runtime not found at MCR_ROOT=$MCR_ROOT" >&2
  echo "Set MCR_ROOT to your MATLAB / MATLAB Runtime R2025b install." >&2
  exit 1
fi

export LD_LIBRARY_PATH="$MCR_ROOT/runtime/glnxa64:$MCR_ROOT/bin/glnxa64:$MCR_ROOT/sys/os/glnxa64:$MCR_ROOT/extern/bin/glnxa64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

ARGS=("$@")
if [[ ${#ARGS[@]} -eq 0 ]]; then
  ARGS=(-m integration)
fi

exec "$ROOT/streamlit/venv/bin/python" -m pytest "${ARGS[@]}"

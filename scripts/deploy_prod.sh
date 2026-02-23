#!/bin/bash
# Deploy to production server at 49.12.232.89.
#
# Usage:
#   ./scripts/deploy_prod.sh             # Sync + restart Streamlit
#   ./scripts/deploy_prod.sh --matlab    # Also rebuild matlab-algorithm image
#
# The compiled MATLAB binary (matlab/Compiled/) is always synced if present.
# Use --matlab when you've recompiled and need the server image rebuilt too.
#
# Prerequisites on server (one-time setup):
#   mkdir -p /opt/nsm-poc/data
#   Create /opt/nsm-poc/.env with: HOST_DATA_DIR=/opt/nsm-poc/data

set -euo pipefail

PROD_HOST="49.12.232.89"
PROD_USER="root"
PROD_DIR="/opt/nsm-poc"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REBUILD_MATLAB=false
if [[ "${1:-}" == "--matlab" ]]; then
    REBUILD_MATLAB=true
fi

echo "==> Syncing project to ${PROD_USER}@${PROD_HOST}:${PROD_DIR} ..."
rsync -az --delete \
    --exclude='.git/' \
    --exclude='.claude/' \
    --exclude='.env' \
    --exclude='data/' \
    --exclude='DemoData/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.egg-info/' \
    --exclude='MATLAB_Runtime*/' \
    "$PROJECT_ROOT/" \
    "${PROD_USER}@${PROD_HOST}:${PROD_DIR}/"

if $REBUILD_MATLAB; then
    echo "==> Rebuilding matlab-algorithm image on server..."
    ssh "${PROD_USER}@${PROD_HOST}" "
        set -e
        cd ${PROD_DIR}
        docker build -t matlab-algorithm:latest ./matlab
    "
fi

echo "==> Rebuilding Streamlit image and restarting stack..."
ssh "${PROD_USER}@${PROD_HOST}" "
    set -e
    cd ${PROD_DIR}
    docker compose up -d --build
"

echo ""
echo "Done. App available at http://${PROD_HOST}:8501"

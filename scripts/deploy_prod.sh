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

PROD_HOST_IPV6="2a01:4f8:c014:1089::1"
PROD_HOST_IPV4="49.12.232.89"  # kept for reference / app URL display
PROD_USER="root"
PROD_DIR="/opt/nsm-poc"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

REBUILD_MATLAB=false
if [[ "${1:-}" == "--matlab" ]]; then
    REBUILD_MATLAB=true
fi

echo "==> Syncing project to ${PROD_USER}@${PROD_HOST_IPV4}:${PROD_DIR} ..."
rsync -az --delete \
    -e "ssh -6" \
    --exclude='.git/' \
    --exclude='.claude/' \
    --exclude='.env' \
    --exclude='streamlit/venv' \
    --exclude='data/' \
    --exclude='DemoData/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='*.egg-info/' \
    --exclude='MATLAB_Runtime*/' \
    "$PROJECT_ROOT/" \
    "${PROD_USER}@[${PROD_HOST_IPV6}]:${PROD_DIR}/"

if $REBUILD_MATLAB; then
    echo "==> Rebuilding matlab-algorithm image on server..."
    ssh -6 "${PROD_USER}@${PROD_HOST_IPV6}" "
        set -e
        cd \"${PROD_DIR}\"
        docker build -t matlab-algorithm:latest ./matlab
    " || { echo "ERROR: remote matlab image build failed"; exit 1; }
fi

echo "==> Rebuilding Streamlit image and restarting stack..."
ssh -6 "${PROD_USER}@${PROD_HOST_IPV6}" "
    set -e
    cd \"${PROD_DIR}\"
    docker compose up -d --build
" || { echo "ERROR: remote stack restart failed"; exit 1; }

echo ""
echo "Done. App available at http://${PROD_HOST_IPV4}:8501"

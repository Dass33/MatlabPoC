#!/bin/sh
set -e

SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

echo "==> Step 1/4: Compiling MATLAB source..."
"$SCRIPT_DIR/compile_matlab.sh"

echo "==> Step 2/4: Building MATLAB Docker image..."
"$SCRIPT_DIR/build_matlab.sh"

echo "==> Step 3/4: Building Streamlit Docker image..."
"$SCRIPT_DIR/build_streamlit.sh"

echo "==> Step 4/4: Restarting stack..."
cd "$PROJECT_ROOT"
docker compose down
docker compose up -d

echo ""
echo "Done. Streamlit is available at http://localhost:8501"
echo "Follow logs with: docker compose logs -f"

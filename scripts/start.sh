#!/bin/sh
set -e

SCRIPT_DIR=$(dirname "$0")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR/..")

echo "==> Step 1/3: Compiling MATLAB source..."
"$SCRIPT_DIR/compile_matlab.sh"

echo "==> Step 2/3: Building Docker image..."
"$SCRIPT_DIR/build_streamlit.sh"

echo "==> Step 3/3: Restarting stack..."
cd "$PROJECT_ROOT"
docker compose down
docker compose up -d

echo ""
echo "Done. Streamlit is available at http://localhost:8501"
echo "Follow logs with: docker compose logs -f"

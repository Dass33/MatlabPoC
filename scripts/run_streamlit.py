#!/usr/bin/env python3
"""
Runs the Streamlit application using the python virtual environment.
"""

import os
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parents[1]

    # Load environment variables
    env_path = project_root / ".env"
    if env_path.is_file():
        print(f"Loading environment variables from {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    os.environ[k] = v

    # Determine the path to streamlit in the virtual environment
    if sys.platform == "win32":
        streamlit_bin = (
            project_root / "streamlit" / "venv" / "Scripts" / "streamlit.exe"
        )
    else:
        streamlit_bin = project_root / "streamlit" / "venv" / "bin" / "streamlit"

    if not streamlit_bin.exists():
        print(
            f"Error: Streamlit executable not found at {streamlit_bin}.",
            file=sys.stderr,
        )
        print(
            "Please run 'python scripts/setup.py' first to create the virtual environment.",
            file=sys.stderr,
        )
        sys.exit(1)

    cmd = [
        str(streamlit_bin),
        "run",
        str(project_root / "streamlit" / "main.py"),
        "--server.enableStaticServing",
        "true",
    ]

    print(f"Starting Streamlit: {' '.join(cmd)}")
    try:
        # Run streamlit in the project root directory
        subprocess.run(cmd, cwd=project_root, check=True)
    except KeyboardInterrupt:
        print("\nStreamlit stopped.")
    except subprocess.CalledProcessError as e:
        print(f"Streamlit process exited with error: {e}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()

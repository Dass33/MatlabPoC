#!/usr/bin/env python3
"""
Docker image builder for Streamlit frontend.
"""

import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parents[1]
    print(f"Project root resolved to: {project_root}")

    # Build streamlit Docker image
    print("Building Docker image matlabpoc-streamlit:latest...")
    try:
        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                "matlabpoc-streamlit:latest",
                "-f",
                "streamlit/Dockerfile",
                ".",
            ],
            cwd=project_root,
            check=True,
        )
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Please make sure Docker is installed and running.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error building Docker image: {e}", file=sys.stderr)
        sys.exit(1)

    # Tag docker image
    print("Tagging image as dass33/nsm-streamlit:latest...")
    try:
        subprocess.run(
            [
                "docker",
                "tag",
                "matlabpoc-streamlit:latest",
                "dass33/nsm-streamlit:latest",
            ],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error tagging Docker image: {e}", file=sys.stderr)
        sys.exit(1)

    print("Docker build and tag completed successfully.")


if __name__ == "__main__":
    main()

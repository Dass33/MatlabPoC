#!/usr/bin/env python3
"""
Deploy script to build and push the Docker image to Docker Hub.
"""

import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parents[1]
    print(f"Project root resolved to: {project_root}")

    print("Building Docker image dass33/nsm-streamlit:latest...")
    try:
        subprocess.run(
            [
                "docker",
                "build",
                "-t",
                "dass33/nsm-streamlit:latest",
                "-f",
                "streamlit/Dockerfile",
                ".",
            ],
            cwd=project_root,
            check=True,
        )
    except FileNotFoundError:
        print(
            "Error: 'docker' command not found. Please make sure Docker is installed.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error building Docker image: {e}", file=sys.stderr)
        sys.exit(1)

    print("Pushing Docker image to Docker Hub...")
    try:
        subprocess.run(
            ["docker", "push", "dass33/nsm-streamlit:latest"],
            cwd=project_root,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error pushing Docker image: {e}", file=sys.stderr)
        sys.exit(1)

    print("Done. Watchtower will pick up changes within 5 minutes.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
MATLAB compilation script.
Compiles the MATLAB source files to a standalone executable and a Python package.
"""

import subprocess
import sys
from pathlib import Path

# Must match the MCR_IMAGE default in streamlit/Dockerfile.
MCR_IMAGE_NAME = "nsm-mcr"


def main():
    project_root = Path(__file__).resolve().parents[1]
    print(f"Project root resolved to: {project_root}")

    # 1. Compile MATLAB standalone application
    compiled_dir = project_root / "matlab" / "Compiled"
    compiled_dir.mkdir(parents=True, exist_ok=True)

    # Run mcc command for AnalyzeExperimentApp
    cmd1 = [
        "matlab",
        "-batch",
        "mcc -m ../nsm-data-analysis/AnalyzeExperimentApp.m -a ../nsm-data-analysis/ -o AnalyzeExperimentApp",
    ]
    print("Compiling AnalyzeExperimentApp...")
    try:
        subprocess.run(cmd1, cwd=compiled_dir, check=True)
    except FileNotFoundError:
        print(
            "Error: 'matlab' command not found in your PATH. Please make sure MATLAB is installed and added to your system PATH.",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error during MATLAB compilation: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Compile Python package
    py_package_dir = compiled_dir / "PythonPackage"
    py_package_dir.mkdir(parents=True, exist_ok=True)

    # Run mcc command for PythonPackage
    cmd2 = [
        "matlab",
        "-batch",
        "mcc -W python:nsm_algorithms "
        "../../nsm-data-analysis/runOutlierFiltering.m "
        "../../nsm-data-analysis/runIocCalibration.m "
        "../../nsm-data-analysis/runPostprocessing.m "
        "../../nsm-data-analysis/runPopulationAnalysis.m "
        "-a ../../nsm-data-analysis/",
    ]
    print("Compiling Python Package (nsm_algorithms)...")
    try:
        subprocess.run(cmd2, cwd=py_package_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during Python Package compilation: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Build the MATLAB Runtime base image for streamlit/Dockerfile.
    #
    # createDockerImage installs only the runtime products named in the
    # buildresult.json it is given, which is ~2.9GB against the ~7.2GB in the
    # stock containers.mathworks.com/matlab-runtime image.
    #
    # Only the Python package's manifest is passed: its product set is a strict
    # superset of the standalone app's (it adds the Python Target addon), and
    # passing both paths makes createDockerImage silently use just the first --
    # which drops that addon and leaves nsm_algorithms.initialize() unable to
    # load.
    py_buildresult = py_package_dir / "buildresult.json"
    if not py_buildresult.is_file():
        print(f"Error: {py_buildresult} not found; did mcc fail?", file=sys.stderr)
        sys.exit(1)

    docker_context = compiled_dir / "mcr_docker"
    cmd3 = [
        "matlab",
        "-batch",
        "compiler.runtime.createDockerImage("
        f"'{py_buildresult}', "
        f"ImageName='{MCR_IMAGE_NAME}', "
        f"DockerContext='{docker_context}', "
        "VerbosityLevel='concise')",
    ]
    print(f"Building MATLAB Runtime image {MCR_IMAGE_NAME}...")
    try:
        subprocess.run(cmd3, cwd=compiled_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error building MATLAB Runtime image: {e}", file=sys.stderr)
        sys.exit(1)

    print("MATLAB compilation complete.")


if __name__ == "__main__":
    main()

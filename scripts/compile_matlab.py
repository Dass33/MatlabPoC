#!/usr/bin/env python3
"""
MATLAB compilation script.
Compiles the MATLAB source files to a standalone executable and a Python package.
"""

import subprocess
import sys
from pathlib import Path


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

    print("MATLAB compilation complete.")


if __name__ == "__main__":
    main()

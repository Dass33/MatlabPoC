#!/usr/bin/env python3
"""
Setup script for MatlabPoC.
It handles git submodules, copying configuration templates, creating virtual environments,
installing python requirements.
"""

import shutil
import subprocess
import sys
from pathlib import Path


def main():
    project_root = Path(__file__).resolve().parents[1]
    print(f"Initializing MatlabPoC setup at project root: {project_root}\n")

    # 1. Initialize and update git submodules
    print("==> Step 1/3: Checking git submodules...")
    # Check if we are in a git repository
    git_dir = project_root / ".git"
    if git_dir.exists():
        try:
            print("Initializing and updating git submodules...")
            subprocess.run(
                ["git", "submodule", "update", "--init", "--recursive"],
                cwd=project_root,
                check=True,
            )
            print("Git submodules updated successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to update git submodules via git command: {e}")
            print(
                "If you cloned this repository without git, please ensure the submodules are present."
            )
    else:
        print(
            "Not a git repository or .git folder not found. Skipping git submodule update."
        )

    # 2. Set up environment file (.env)
    print("\n==> Step 2/3: Setting up environment configuration...")
    env_file = project_root / ".env"
    env_example = project_root / ".env.example"
    if not env_file.exists():
        if env_example.exists():
            print(f"Copying {env_example.name} to {env_file.name}...")
            shutil.copy(env_example, env_file)
            print(f"Created configuration file: {env_file}")
        else:
            print(
                f"Warning: {env_example.name} not found. Creating a blank {env_file.name} file."
            )
            env_file.touch()
    else:
        print(f"Configuration file {env_file.name} already exists.")

    # 3. Create virtual environment and install requirements
    print("\n==> Step 3/3: Setting up virtual environment for Streamlit...")
    venv_dir = project_root / "streamlit" / "venv"
    requirements_file = project_root / "streamlit" / "requirements.txt"

    # Create virtual environment if it doesn't exist
    if not venv_dir.exists():
        print(f"Creating python virtual environment at {venv_dir}...")
        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
            print("Virtual environment created.")
        except subprocess.CalledProcessError as e:
            print(f"Error creating virtual environment: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(f"Virtual environment at {venv_dir} already exists.")

    # Install requirements
    if sys.platform == "win32":
        pip_bin = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_bin = venv_dir / "bin" / "pip"

    if not pip_bin.exists():
        print(f"Error: pip executable not found at {pip_bin}", file=sys.stderr)
        sys.exit(1)

    if requirements_file.exists():
        print("Installing dependencies from requirements.txt...")
        try:
            subprocess.run(
                [str(pip_bin), "install", "-r", str(requirements_file)], check=True
            )
            print("Python dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing dependencies: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(
            f"Warning: {requirements_file} not found. Skipping dependency installation."
        )

    dev_requirements = project_root / "requirements-dev.txt"
    if dev_requirements.exists():
        print("Installing developer dependencies from requirements-dev.txt...")
        try:
            subprocess.run(
                [str(pip_bin), "install", "-r", str(dev_requirements)], check=True
            )
            print("Developer dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing developer dependencies: {e}", file=sys.stderr)
            sys.exit(1)

    print("\nSetup successful! You are ready to develop.")
    print("To run the local development server:")
    print("  python scripts/run_streamlit.py")


if __name__ == "__main__":
    main()

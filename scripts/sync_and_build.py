#!/usr/bin/env python3
import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def run_command(command, cwd=None):
    print(f"Running: {' '.join(command)}")
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(result.returncode)
    return result.stdout


def main():
    parser = argparse.ArgumentParser(
        description="Sync MATLAB source and rebuild SimPackage wheel."
    )
    parser.add_argument("matlab_repo", help="Path to the source MATLAB repository")
    parser.add_argument(
        "--skip-mcc", action="store_true", help="Skip MATLAB compilation (mcc)"
    )
    parser.add_argument(
        "--push", action="store_true", help="Push changes to git after build"
    )

    args = parser.parse_args()

    repo_root = Path(__file__).parent.parent.absolute()
    matlab_repo = Path(args.matlab_repo).absolute()

    if not matlab_repo.exists():
        print(f"Error: MATLAB repo path '{matlab_repo}' does not exist.")
        sys.exit(1)

    # 1. Sync Files
    print(f"--- Syncing files from {matlab_repo} ---")
    src_m = matlab_repo / "analyze_image.m"
    src_tools = matlab_repo / "tools"

    dest_m = repo_root / "matlab_src" / "analyze_image.m"
    dest_tools = repo_root / "matlab_src" / "tools"

    if src_m.exists():
        shutil.copy2(src_m, dest_m)
        print(f"Copied {src_m.name}")

    if src_tools.exists():
        if dest_tools.exists():
            shutil.rmtree(dest_tools)
        shutil.copytree(src_tools, dest_tools)
        print("Synced tools/ directory")

    # 2. MATLAB Compilation (mcc)
    if not args.skip_mcc:
        print("--- Running MATLAB Compiler (mcc) ---")
        # Ensure we are in the repo root to run mcc
        mcc_cmd = [
            "mcc",
            "-W",
            "python:SimPackage",
            "-T",
            "link:lib",
            str(dest_m),
            "-a",
            str(dest_tools),
            "-d",
            str(repo_root / "SimPackage"),
        ]
        run_command(mcc_cmd)
    else:
        print("Skipping MATLAB compilation (mcc) as requested.")

    # 3. Build Wheel
    print("--- Building Python Wheel ---")
    sim_pkg_dir = repo_root / "SimPackage"
    # Use the venv or system python to build the wheel
    run_command([sys.executable, "setup.py", "bdist_wheel"], cwd=sim_pkg_dir)

    # 4. Move Wheel to libs/
    print("--- Moving wheel to libs/ ---")
    dist_dir = sim_pkg_dir / "dist"
    libs_dir = repo_root / "libs"
    libs_dir.mkdir(exist_ok=True)

    # Remove old wheels
    for old_whl in libs_dir.glob("*.whl"):
        old_whl.unlink()

    for whl in dist_dir.glob("*.whl"):
        shutil.copy2(whl, libs_dir / whl.name)
        print(f"Moved {whl.name} to libs/")

    # 5. Git Operations
    print("--- Preparing Git Commit ---")
    run_command(
        [
            "git",
            "add",
            "matlab_src/",
            "libs/",
            "SimPackage/setup.py",
            "SimPackage/pyproject.toml",
        ]
    )

    # Check for changes
    status = run_command(["git", "status", "--porcelain"])
    if status.strip():
        run_command(
            ["git", "commit", "-m", "chore: sync matlab source and rebuild wheel"]
        )
        if args.push:
            print("Pushing changes...")
            run_command(["git", "push"])
    else:
        print("No changes to commit.")

    print("\nDone! The MATLAB package is rebuilt and ready for deployment.")


if __name__ == "__main__":
    main()

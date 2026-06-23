#!/usr/bin/env python3
"""
Compiles MATLAB code, builds the docker container, and restarts the docker-compose stack.
"""
import subprocess
import sys
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parents[1]
    scripts_dir = project_root / "scripts"
    
    print("==> Step 1/3: Compiling MATLAB source...")
    try:
        subprocess.run([sys.executable, str(scripts_dir / "compile_matlab.py")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Compilation failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("==> Step 2/3: Building Docker image...")
    try:
        subprocess.run([sys.executable, str(scripts_dir / "build_streamlit.py")], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Docker build failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("==> Step 3/3: Restarting stack...")
    try:
        # Run docker compose down and up -d
        subprocess.run(["docker", "compose", "down"], cwd=project_root, check=True)
        subprocess.run(["docker", "compose", "up", "-d"], cwd=project_root, check=True)
    except FileNotFoundError:
        print("Error: 'docker' command not found. Make sure Docker is installed.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Docker Compose failed: {e}", file=sys.stderr)
        sys.exit(1)
    
    print("\nDone. Streamlit is available at http://localhost:8501")
    print("Follow logs with: docker compose logs -f")

if __name__ == "__main__":
    main()

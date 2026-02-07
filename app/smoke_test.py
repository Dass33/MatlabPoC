import os
import sys

# Setup paths to match app/main.py
current_file = os.path.abspath(__file__)
app_dir = os.path.dirname(current_file)
project_root = os.path.dirname(app_dir)
sim_package_path = os.path.join(project_root, 'SimPackage')

if sim_package_path not in sys.path:
    sys.path.insert(0, sim_package_path)
if project_root not in sys.path:
    sys.path.append(project_root)

def test_matlab_binding():
    print("Checking for SimPackage...")
    try:
        import SimPackage
        print("SimPackage found!")
    except ImportError as e:
        print(f"FAILED: SimPackage not found: {e}")
        return False

    print("Checking for matlab engine...")
    try:
        import matlab
        print("matlab engine found!")
    except ImportError as e:
        print(f"FAILED: matlab engine not found: {e}")
        return False

    print("Attempting to initialize SimPackage...")
    try:
        my_lib = SimPackage.initialize()
        print("SUCCESS: SimPackage initialized successfully!")
        my_lib.terminate()
        return True
    except Exception as e:
        print(f"FAILED: Error during SimPackage initialization: {e}")
        return False

if __name__ == "__main__":
    if test_matlab_binding():
        print("
Smoke test PASSED!")
        sys.exit(0)
    else:
        print("
Smoke test FAILED!")
        sys.exit(1)

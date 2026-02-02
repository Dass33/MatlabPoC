import numpy as np
import SimPackage
import matlab

def run_demo():
    print("PYTHON: Initializing MATLAB Runtime...")
    my_lib = SimPackage.initialize()

    # Create dummy 2D data (Time, Space)
    # reference.m uses Kt=159, so let's use at least that many time points
    time_points = 200
    space_points = 50
    raw_data = np.random.rand(time_points, space_points)
    
    # Convert to MATLAB double array
    input_data = matlab.double(raw_data.tolist())
    
    print("PYTHON: Calling MATLAB 'preprocessing' function...")
    
    # Positional name-value pairs (traditional way)
    x = my_lib.preprocessing(input_data, 'Kt', 159.0)

    # Convert result back to numpy for easier handling
    result = np.array(x)
    print(f"PYTHON: Preprocessing completed.")
    print(f"PYTHON: Input shape: {raw_data.shape}")
    print(f"PYTHON: Output shape: {result.shape}")
    print(f"PYTHON: Result sample (first 2x2):\n{result[:2, :2]}")
    
    my_lib.terminate()

if __name__ == "__main__":
    run_demo()

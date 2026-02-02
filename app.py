import numpy as np
import SimPackage
import matlab

def run_demo():
    print("PYTHON: Initializing MATLAB Runtime...")
    my_lib = SimPackage.initialize()

    raw_data = np.random.rand(100).tolist()
    
    input_data = matlab.double(raw_data)
    
    # window_size = 5.0 

    print("PYTHON: Calling MATLAB function...")
    
    x = my_lib.preprocessing(input_data)
    #result_smooth, result_peak = my_lib.my_magic_function(input_data, window_size, nargout=2)
    print(x)

    # Process results
    # peak = np.array(result_peak).flatten()[0]
    #print(f"PYTHON: Success! The MATLAB calculation returned a peak of {peak:.4f}")
    
    my_lib.terminate()

if __name__ == "__main__":
    run_demo()

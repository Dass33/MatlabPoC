function [smoothed_data, peak_value] = my_magic_function(input_data, window_size)
    % MY_MAGIC_FUNCTION: A dummy scientific function
    % Input: A list of noisy numbers (input_data)
    % Output: Smoothed numbers and the maximum peak
    
    % 1. Ensure input is a double array (Safety for Python inputs)
    data = double(input_data);
    
    % 2. Perform a calculation (e.g., moving average)
    % Note: 'movmean' is a standard MATLAB function
    smoothed_data = movmean(data, window_size);
    
    % 3. Find a metric
    peak_value = max(smoothed_data);
    
    % 4. Debug print (will show in your terminal, good for testing)
    fprintf('MATLAB: processed %d points. Max peak is %.2f\n', length(data), peak_value);
end

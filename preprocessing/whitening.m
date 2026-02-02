function X_tilde = whitening(X, options)
    
    arguments
        X
        options.method = 'std_division'
    end

    switch options.method

        case 'std_division'

            % global std
            X_std_iqr = 0.7413 * iqr(X(:));
        
            % time-std
            X_time_std_iqr = 0.7413 * iqr(X);
        
        case 'none'

            X_std_iqr = 1;      
            X_time_std_iqr = 1;
    end

    % normalization to keep global std
    X_tilde = (X ./ X_time_std_iqr) * X_std_iqr;

end
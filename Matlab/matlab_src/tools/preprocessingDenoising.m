function Y = preprocessingDenoising(R, options)

    arguments
        R

        options.Kt = 101
        options.sigma_x = 1
        options.spaceFilter = 'gaussian'
        options.chainOrder = 'preprocessing_denoising'
        options.defluctuationMethod = 'mean'
        options.bacgroundEstimationMethod = 'padded_movmean'
        options.backgroundRemovalMethod = 'subtract'
        options.whiteningMethod = 'std_division'
        options.timeFilter = 'none'
        options.nonLinearFilter = 'none'

        options.k_max = 2
        options.log_k_max = 5
        options.Kx = 51
        options.x_max = 16.47
        options.sigma_t = eps

    end

    switch options.chainOrder
        
        case 'preprocessing_denoising'

            D = defluctuation(R, method=options.defluctuationMethod, Kx=options.Kx);
        
            B = backgroundEstimation(D, Kt=options.Kt, method=options.bacgroundEstimationMethod);
        
            X_tilde = backgroundRemoval(D, B, method=options.backgroundRemovalMethod);
        
            X = whitening(X_tilde, method=options.whiteningMethod);
        
            Y = denoising(X, ...
                spaceFilter=options.spaceFilter, ...
                sigma_x=options.sigma_x, ...
                timeFilter=options.timeFilter, ...
                sigma_t=options.sigma_t, ...
                nonLinearFilter=options.nonLinearFilter, ...
                k_max=options.k_max, ...
                log_k_max=options.log_k_max, ...
                x_max=options.x_max);

        case 'denoising_preprocessing'
                
            X = denoising(R, ...
                spaceFilter=options.spaceFilter, ...
                sigma_x=options.sigma_x, ...
                timeFilter=options.timeFilter, ...
                sigma_t=options.sigma_t, ...
                nonLinearFilter=options.nonLinearFilter, ...
                k_max=options.k_max, ...
                log_k_max=options.log_k_max, ...
                x_max=options.x_max);

            D = defluctuation(X, method=options.defluctuationMethod, Kx=options.Kx);
        
            B = backgroundEstimation(D, Kt=options.Kt, method=options.bacgroundEstimationMethod);
        
            X_tilde = backgroundRemoval(D, B, method=options.backgroundRemovalMethod);
        
            Y = whitening(X_tilde, method=options.whiteningMethod);

    end

end
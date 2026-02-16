function W = denoising(X, options)

    arguments

        X

        options.spaceFilter = 'imgaussfilt'
        options.sigma_x = 1
        options.timeFilter = 'none'
        options.sigma_t = eps
        options.nonLinearFilter = 'none'

        options.k_max = 2; % default in imgaussfilt
        options.log_k_max = 5; 
        options.x_max = 16.47
        % options.x_max = 22.76
        
        options.hx = 1;

    end

        switch options.spaceFilter

            case 'none'
                Y = X;

            case 'imgaussfilt'
                Y = imgaussfilt(X, [eps, options.sigma_x]);

            case 'gaussian'
                hx = gaussian(options.sigma_x, k_max=options.k_max);
                Y = paddedFiltering(X, hx);

            case 'lowered_gaussian'
                hx = gaussian(options.sigma_x, k_max=options.k_max);
                hx = hx - mean(hx);
                Y = paddedFiltering(X, hx);

            case 'laplacean_of_gaussian'
                hx = laplacean_of_gaussian(options.sigma_x, k_max=options.log_k_max);
                Y = paddedFiltering(X, hx);

            case 'jinc'
                a = 1/options.sigma_x * 4.43/(2*sqrt(2*log(2)));
                hx = jinc(a, x_max=options.x_max);
                hx = hx - mean(hx);
                Y = paddedFiltering(X, hx);
            case 'psf'
                Y = paddedFiltering(X, options.hx);
                
        end

        switch options.timeFilter

            case 'none'
                Z = Y;

            case 'imgaussfilt'
                Z = imgaussfilt(Y, [options.sigma_t, eps]);
        end
                
        switch options.nonLinearFilter

            case 'none'
                W = Z;

            case 'nlm'
                Z_std_iqr = std_iqr(Z(:));
                W = imnlmfilt(Z, DegreeOfSmoothing=Z_std_iqr);

        end

end
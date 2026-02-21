function thresholded = thresholding(Y, options)
% mh, v1.0, 2026_01_12

    arguments
        Y
        options.peakSign = 'negative'
        options.noise_std
        options.noise_mean
        options.pfa
    end

    switch options.peakSign

        case 'negative'

            tau_neg = negativePeakThreshold(options.noise_std, options.noise_mean, options.pfa);       

            thresholded = Y < tau_neg;

        case 'positive'

            tau_pos = positivePeakThreshold(options.noise_std, options.noise_mean, options.pfa);       
            
            thresholded = Y > tau_pos;

        case 'negative-positive'

            tau_neg = negativePeakThreshold(options.noise_std, options.noise_mean, options.pfa/2);       
            tau_pos = positivePeakThreshold(options.noise_std, options.noise_mean, options.pfa/2);       
            
            thresholded = (Y < tau_neg) | (Y > tau_pos);

    end
end
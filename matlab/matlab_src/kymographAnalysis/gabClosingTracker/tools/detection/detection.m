function Detections = detection(Y, options)    
% mh, v1.0, 2026_01_12

    arguments
        Y
        options.peakSign
        options.pfa
        options.localOptimumRange
        options.boarderRange
    end

    % noise statistic estimate
    Y_std_iqr = std_iqr(Y(:));
    Y_median = median(Y(:));
    
    % statistically significant thresholding
    thresholded = thresholding(Y, ...
        peakSign=options.peakSign, noise_std=Y_std_iqr, noise_mean=Y_median, pfa=options.pfa);
    
    % local optimum    
    switch options.peakSign
        case 'negative'
            localOptimas = findLocalMinima(Y, options.localOptimumRange);
    
        case 'positive'
            localOptimas = findLocalMaxima(Y, options.localOptimumRange);
    
        case 'negative-positive'
            localOptimas = findLocalMinima(Y, options.localOptimumRange) | ...
                findLocalMaxima(Y, options.localOptimumRange);
    end

    % remove boarder minimas  
    localOptimas(:,1:options.boarderRange) = false;
    localOptimas(:,(end-options.boarderRange+1):end) = false;    

    % make structure with detections
    Detections.peakSign = options.peakSign;
    Detections.noise_std = Y_std_iqr;
    Detections.noise_mean = Y_median;
    Detections.pfa = options.pfa;

    thresholdedLocalOptimas = thresholded & localOptimas;
    [Detections.position, Detections.frame] = find(thresholdedLocalOptimas.');

    Detections.intensity = Y(sub2ind(size(Y), Detections.frame, Detections.position));    
    Detections.snr = abs(Detections.intensity - Detections.noise_mean ) / Detections.noise_std;    
    Detections.nDetections = length(Detections.frame);

end
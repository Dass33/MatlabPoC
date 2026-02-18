function Detections = detection(Y, options)    
                
    arguments
        Y
        options.pfa = 1e-4
        options.localMinRange = 6
    end

    % noise std estimate
    Y_std_iqr = std_iqr(Y(:));
    
    % statistically significant thresholding
    thresholded = thresholding(Y, Y_std_iqr, options.pfa);
    
    % local minimum 
    localMinimas = findLocalMinima(Y, options.localMinRange);

    % remove boarder minimas
    localMinimas(:,1:options.localMinRange) = false;
    localMinimas(:,(end-options.localMinRange+1):end) = false;
    
    % structure with detections
    Detections = makeDetectionStructure(...
        thresholded, localMinimas, Y, Y_std_iqr, options.pfa);

end
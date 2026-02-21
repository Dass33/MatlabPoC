function localMaximas = findLocalMaxima(Y, localMaxRange)

    % search for local maxima in rows
    structuringElement = ones(1,2*localMaxRange+1);

    Y_dilate = imdilate (Y, structuringElement);
    
    localMaximas = abs(Y-Y_dilate) < 1e-8;

end
function localMaximas = findLocalMinima(Y, localMinRange)

    % search for local minima in rows
    structuringElement = ones(1,2*localMinRange+1);

    Y_erode = imerode(Y, structuringElement);
    
    % localMaximas = (Y-Y_erode) == 0; % not robust
    localMaximas = abs(Y-Y_erode) < 1e-8;

end
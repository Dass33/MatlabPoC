function Y = paddedFiltering(X, h)
    
    filterSize = length(h);
    filterRange = (filterSize-1)/2;

    % padding
    X_pad = padarray(X, [0, filterRange], 'replicate');
    
    % filtering over space dimension
    Y = filter(h, 1, X_pad, [], 2); 
    
    % remove padded parts
    Y(:, 1:2*filterRange) = [];

end
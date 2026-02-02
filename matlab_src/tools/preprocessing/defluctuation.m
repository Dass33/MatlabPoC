function D = defluctuation(R, options)

    arguments
        R
        options.method = 'mean' 
        options.Kx = 51
    end
    
    switch options.method

        case 'mean'

            R_space_average = mean(R,2);
            R_total_average = mean(R(:));
            
        case 'median'

            R_space_average = median(R,2);
            R_total_average = median(R(:));

        case 'movmean'

            R_space_average = movmean(R, options.Kx, 2);
            R_total_average = mean(R(:));

        case 'padded_movmean'
            
            R_space_average = movmean( padarray(R,[0,(options.Kx-1)/2],"replicate") , options.Kx, 2, Endpoints="discard");
            R_total_average = mean(R(:));

        case 'non'

            R_space_average = 1;
            R_total_average = 1;

    end
    
    % defluctuation
    D = R ./ R_space_average; 

    % normalization to equal total average
    D = R_total_average * D;
    
end
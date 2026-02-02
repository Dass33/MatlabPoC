function B = backgroundEstimation(D, options)

    arguments
        D

        options.Kt=1
        options.method = 'padded_movmean'
    end

    switch options.method

        case 'movmean'
            B = movmean(D, options.Kt);

        case 'padded_movmean'
            B = movmean(padarray(D,[(options.Kt-1)/2,0],"replicate"), options.Kt, Endpoints="discard");

        case 'movmedian'
            B = movmedian(D, options.Kt);

        case 'padded_movmedian'
            B = movmedian(padarray(D,[(options.Kt-1)/2,0],"replicate"), options.Kt, Endpoints="discard");

    end       
    
end
function h = gaussian(sigma, options)

    arguments

        sigma

        options.k_max = 2; % default value in imgaussfilt

    end

    range = ceil( options.k_max*sigma ); % as in imgaussfilt
    
    x = -range:range;
    
    h = 1/sqrt(2*pi*sigma^2) * exp(-1/(2*sigma^2) * x.^2 );

    h = h / sum(h);

end
function [h,x] = laplacean_of_gaussian(sigma, options)

    arguments

        sigma

        options.k_max = 5;

    end

    range = floor( options.k_max*sigma );

    x = -range:range;  
    
    h = (1 - x.^2 / sigma^2) .* exp(-x.^2 / (2*sigma^2)); 

end
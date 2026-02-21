function Y = normalize2d(X, options)

    arguments
        X
        options.method = 'min0_max1'
    end

    switch options.method

        case 'min0_max1'

            Y = (X - min(X(:))) / (max(X(:)) - min(X(:)));

        case 'mean0_max1'

            mean_x = mean(X(:));
            max_x = max(X(:));

            Y = 1/(max_x-mean_x) * X - mean_x / (max_x - mean_x);

    end

return
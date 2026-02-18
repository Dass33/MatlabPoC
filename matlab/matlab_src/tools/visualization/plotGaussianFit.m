function plotGaussianFit(data, options)

    arguments

        data

        options.DisplayName = 'fitted Gaussian'
        options.color = 'k'
        options.k_max = 5

    end

mu = mean(data(:));
sigma = std(data(:));

x = linspace(mu - options.k_max*sigma, mu + options.k_max*sigma);
y = 1/sqrt(2*pi*sigma^2) * exp( - (x-mu).^2 / (2*sigma^2));

plot(x, y, options.color, DisplayName=options.DisplayName)
function [z, w, res] = optimalLinearCombinationND(X)
%OPTIMALLINEARCOMBINATIONND
% Maximizes mean/std ratio of a linear combination of N-dimensional measurements
%
% INPUT:
%   X : NxM matrix, rows = samples, columns = measured quantities
%
% OUTPUT:
%   z   : Nx1 combined measurement (maximal resolution)
%   w   : Mx1 vector of optimal weights
%   res : achieved resolution (mean/std)

    [N, M] = size(X);

    if M < 2
        error('Input must have at least 2 dimensions (columns).');
    end

    % --- compute mean vector (Mx1)
    mu = mean(X, 1)';

    % --- covariance matrix (MxM)
    Sigma = cov(X);

    % --- optimal weights
    w = Sigma \ mu;   % equivalent to inv(Sigma)*mu

    % --- linear combination
    z = X * w;

    % --- resulting resolution
    res = mean(z)/std(z);
end
function [z, w, res] = optimalLinearCombination(X)
%OPTIMALLINEARCOMBINATION Maximizes mean/std ratio of linear combination
% INPUT:
%   X : Nx2 matrix, columns = measured quantities (physical, non-zero mean)
% OUTPUT:
%   z : Nx1 combined measurement with maximal resolution
%   w : 2x1 optimal weights
%   res : achieved resolution (mean/std)

    % Compute mean vector and covariance
    mu = mean(X,1)';       % 2x1
    Sigma = cov(X);        % 2x2

    % Optimal weights
    w = Sigma \ mu;        % equivalent to inv(Sigma)*mu

    % Apply linear combination
    z = X * w;

    % Compute resulting resolution
    res = mean(z)/std(z);
end
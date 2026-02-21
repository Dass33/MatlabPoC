function [X_rot, V, D, mu] = rotateAlongPrincipalAxisND(X)
%ROTATEALONGPRINCIPALAXISND Rotates N-dimensional data into principal axes
%
% INPUT:
%   X : NxM data matrix (rows = samples, columns = variables)
%
% OUTPUT:
%   X_rot : NxM rotated data (principal-axis coordinates)
%   V     : MxM rotation matrix (eigenvectors, columns = principal axes)
%   D     : MxM diagonal matrix of variances (eigenvalues)
%   mu    : 1xM mean of original data

    [N, M] = size(X);

    if N < 2 || M < 2
        error('Input must be at least 2x2 data.');
    end

    % --- compute mean vector
    mu = mean(X, 1);

    % --- center data
    Xc = X - mu;

    % --- covariance matrix
    Sigma = cov(Xc);

    % --- eigen-decomposition
    [V, D] = eig(Sigma);

    % --- sort eigenvalues descending (largest first)
    [eigvals, idx] = sort(diag(D), 'descend');
    V = V(:, idx);
    D = diag(eigvals);

    % --- rotate data along principal axes
    X_rot = Xc * V;

end
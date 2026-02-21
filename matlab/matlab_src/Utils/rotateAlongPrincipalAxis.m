function [X_rot, V, D, mu] = rotateAlongPrincipalAxis(X)
%ROTATEALONGPRINCIPALAXIS Rotates 2D data into its principal axes
%
% INPUT:
%   X   : Nx2 data matrix (columns = variables)
%
% OUTPUT:
%   X_rot : Nx2 rotated data (principal-axis coordinates)
%   V     : 2x2 rotation matrix (eigenvectors)
%   D     : 2x2 diagonal matrix of variances (eigenvalues)
%   mu    : 1x2 mean of original data

    % --- sanity check
    if size(X,2) ~= 2
        error('Input must be Nx2 data.');
    end

    % --- subtract mean
    mu = mean(X,1);
    Xc = X - mu;

    % --- covariance matrix
    Sigma = cov(Xc);

    % --- eigen-decomposition
    [V, D] = eig(Sigma);

    % --- sort eigenvalues descending (major axis first)
    [eigvals, idx] = sort(diag(D), 'descend');
    V = V(:,idx);
    D = diag(eigvals);

    % --- rotate data
    X_rot = Xc * V;

end
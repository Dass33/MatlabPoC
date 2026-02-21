function [X_new, theta, R, Sigma] = rotateCoordinateSystem2D(X)
%ROTATECOORDINATESYSTEM2D
% Analyze 2D data and express it in a rotated coordinate system
% whose axes are aligned with the covariance (principal axes).
%
% INPUT:
%   X : Nx2 data matrix (original coordinates, physical values)
%
% OUTPUT:
%   X_new : Nx2 coordinates of the same points in the rotated system
%   theta : rotation angle (radians)
%   R     : rotation matrix (old -> new coordinates)
%   Sigma : covariance matrix of original data

    if size(X,2) ~= 2
        error('Input must be Nx2 data.');
    end

    % --- compute covariance (NO centering beyond what cov does internally)
    Sigma = cov(X);

    % --- extract elements
    sxx = Sigma(1,1);
    syy = Sigma(2,2);
    sxy = Sigma(1,2);

    % --- principal-axis rotation angle
    theta = 0.5 * atan2(2*sxy, sxx - syy);

    % --- rotation matrix (passive rotation: change of basis)
    R = [ cos(theta)  sin(theta);
         -sin(theta)  cos(theta) ];

    % --- transform coordinates into rotated system
    X_new = X * R.';   % transpose because we rotate axes, not points

end
function [beta, stats] = weighted_multireg(p, B, I, w, varargin)
% weighted_multireg  Weighted linear regression for I(x) = a*p + sum b_i * B_i
%
% Inputs:
%   p  - n x 1 vector (predictor p(x))
%   B  - n x 16 matrix (columns B1..B16). If you have fewer/more, it still works.
%   I  - n x 1 response vector
%   w  - n x 1 nonnegative weights (0..1). Can be unnormalized.
% Optional name/value:
%   'NormalizeWeights' (true/false) default true   -- will scale w to sum(w)=1
%   'Ridge'            (lambda >=0) default 0      -- add ridge regularization
%
% Outputs:
%   beta  - 17 x 1 vector [a; b1; ...; b16]
%   stats - struct with fields .mse, .stdErr (approx), .covBeta (if available)

    p = p(:);
    I = I(:);
    w = w(:);
    if size(B,1) ~= numel(I)
        error('B must have same number of rows as I');
    end

    % parse optional args
    defaults = {'NormalizeWeights', true, 'Ridge', 0};
    opts = struct(defaults{:});
    for k=1:2:length(varargin)
        opts.(varargin{k}) = varargin{k+1};
    end

    % build design matrix
    X = [p, B];   % n x m  where m = 1 + size(B,2)

    % normalize weights if requested (sum = 1 is numerically stable)
    if opts.NormalizeWeights
        if sum(w) == 0
            warning('Sum of weights is zero: using uniform weights');
            w = ones(size(w)) / numel(w);
        else
            w = w / sum(w);
        end
    end

    % Use lscov if available (handles vector weights efficiently)
    lambda = opts.Ridge;
    if lambda == 0
        % simple weighted least squares
        beta = lscov(X, I, w);    % returns (X' W X)^{-1} X' W y
    else
        % weighted ridge: solve (X' W X + lambda*I) beta = X' W y
        W = sparse(1:length(w), 1:length(w), w);  % sparse diag
        [n, m] = size(X);
        A = X' * (W * X);
        A = A + lambda * eye(m);          % regularize all coeffs equally
        rhs = X' * (W * I);
        beta = A \ rhs;
    end

    % optional stats (approx)
    % residuals and mse (using effective weights scaling)
    yhat = X * beta;
    resid = I - yhat;
    % weighted MSE
    mse = sum(w .* (resid.^2)) / sum(w);
    % approximate covariance of beta: cov(beta) = (X' W X)^{-1} * mse
    try
        if lambda == 0
            covBeta = inv(X' * (sparse(1:length(w),1:length(w),w) * X)) * mse;
        else
            covBeta = inv(X'*(sparse(1:length(w),1:length(w),w)*X) + lambda*eye(size(X,2))) * mse;
        end
        stdErr = sqrt(diag(covBeta));
    catch
        covBeta = [];
        stdErr = [];
    end

    stats.mse = mse;
    stats.covBeta = covBeta;
    stats.stdErr = stdErr;
end
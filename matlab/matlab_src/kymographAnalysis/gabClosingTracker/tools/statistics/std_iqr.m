function sigma = std_iqr(x)

% Function std_iqr(x) computes robust standard deviation estimation for normal distribution by
% inter-quantile range.

    sigma = 0.7413 * iqr(x); 
    
    % 1/(2*sqrt(2)*erfinv(1/2)) = 0.7413

end

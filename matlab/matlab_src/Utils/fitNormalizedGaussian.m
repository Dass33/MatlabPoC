function params = fitNormalizedGaussian(xdata, ydata, A, relevant, initGuess, plotFlag)
% fitNormalizedGaussian_simple  
% Fit Gaussian normalized by its moving mean using fminsearch (no toolboxes).
%
%   params = fitNormalizedGaussian_simple(xdata, ydata, A, initGuess)
%
%   Inputs:
%       xdata     - vector of x values
%       ydata     - vector of y values (same length as xdata)
%       A         - window size for movmean
%       initGuess - optional initial guess [a, b, c]
%
%   Output:
%       params = [a, b, c]  fitted Gaussian parameters
%
%   Model:
%       y = a * exp(-((x-b)/c).^2);
%       y = y ./ movmean(y, A);

    if nargin < 4
        % Rough default guess
        a0 = max(ydata);
        [~, idxMax] = max(ydata);
        b0 = xdata(idxMax);
        c0 = (max(xdata)-min(xdata))/10;
        initGuess = [a0, b0, c0];
    end

    % Objective: sum of squared errors
    %objFun = @(p) sum((ydata(A+1:end-A) - normalizeGaussian(xdata, p(1), p(2), p(3), A)).^2);
    objFun = @(p) sum((ydata(relevant) - normalizeGaussian(xdata, p(1), p(2), p(3), A, relevant)).^2);


    % Run optimization
    %options = optimset('Display','iter','TolX',1e-6,'TolFun',1e-6);
    %options = optimset('PlotFcns',@optimplotfval);
    options = optimset('TolX',1e-9,'TolFun',1e-9);
    params = fminsearch(objFun, initGuess, options);

    % Plot if requested
    if plotFlag
        yfit = normalizeGaussian(xdata, params(1), params(2), params(3), A, relevant);
        hold off 
        plot(xdata, ydata, 'ko', 'MarkerSize', 6, 'DisplayName','Data'); hold on;
        plot(xdata(relevant), yfit, 'r-', 'LineWidth', 2, 'DisplayName','Fit');
        xlabel('x'); ylabel('y');
        legend('show');
        title(sprintf('Fit results: a=%.3f, b=%.3f, c=%.3f', params(1), params(2), params(3)));
        grid on;
        drawnow
    end

end

function y = normalizeGaussian(x, a, b, c, A, relevant)
    y = 1 + a * exp(-((x-b)./c).^2);
    if A > 0
        y = y ./ movmean(y, 2*A+1);
    end
    y = y(relevant);
end
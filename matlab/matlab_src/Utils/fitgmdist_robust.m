function [MEAN, STD, selected, GMModel] = fitgmdist_robust(X, k, initial, plotResult)

if nargin < 4
    plotResult = false;
end

if nargin < 3
    initial = [];
end

[Nd, Nx] = size(X);


MEAN = NaN( k, Nd);
STD = NaN(k, Nd);
selected_any0 = false(1, Nx);
selected_any = true(1, Nx);

while sum(selected_any ~= selected_any0) > 0

    selected_any0 = selected_any;

    if isempty(initial)
        GMModel = fitgmdist(X(:,selected_any)', k,'CovarianceType','diagonal');
    else
        GMModel = fitgmdist(X(:,selected_any)', k,'CovarianceType','diagonal','Start',initial);
    end

    % extract info about MEAN and STD from GMM model
    R2 = zeros(k, Nx);
    for i = 1:Nd
        MEAN(:,i) = GMModel.mu(:,i);
        STD(:,i) = permute(sqrt(GMModel.Sigma(:,i,:)), [3,2,1]);
        R2 = R2 + ((X(i,:) - MEAN(:,i))./STD(:,i)).^2;
    end
    
    %selected = sum(R2 < 9,1) > 0;
    selected = R2 < 9;
    selected_any = sum(selected,1) > 0;
    
    initial = struct('mu',GMModel.mu,'Sigma',GMModel.Sigma);

    if plotResult

        clear trajectory plotProperties lineParams
        for i = 1:Nd
            plotProperties{i} = repmat('a',1,i);
        end

        for i = 1:Nd
            trajectory.(plotProperties{i}) = X(i,:);
            lineParams.MEAN.(plotProperties{i}) = MEAN(:,i);
            lineParams.STD.(plotProperties{i}) = STD(:,i);
        end

        scatterPlot(trajectory, plotProperties, '.')
        scatterPlot(trajectory, plotProperties, 'o', selected_any, lineParams)

    end
end

MEAN = MEAN';
STD = STD';

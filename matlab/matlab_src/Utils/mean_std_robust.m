function [MEAN, STD, selected, outlierLimitValue_calculated] = mean_std_robust(x, outlierStyle, outlierLimitValue, N)



if nargin < 2
    outlierStyle = 'R2';
else
    if isempty(outlierStyle)
        outlierStyle = 'R2';
    end
end

if nargin < 3
    outlierLimitValue = cell(size(outlierStyle));
    for i = 1:length(outlierLimitValue)
        outlierLimitValue{i} = 'calc';
    end
end

selected = ~isnan(sum(x,1));
selected0 = false(size(selected)); 

while sum(selected ~= selected0) > 0

    if nargin == 4
        MEAN = sum(x(:,selected).*N(:,selected),2)./sum(selected.*N,2);
        STD = sqrt(sum((x(:,selected) - MEAN).^2.*N(:,selected),2)/(sum(selected.*N,2)-1));
    else

        MEAN = mean(x(:,selected), 2);
        STD = std(x(:,selected), 0, 2);
    end
    selected0 = selected;
    [selected, outlierLimitValue_calculated] = findOutliers(x, MEAN, STD, outlierStyle, outlierLimitValue);

end




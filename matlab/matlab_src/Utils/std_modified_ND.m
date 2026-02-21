function [STD, MEAN, selected] = std_modified_ND(x, dim, robustStyle, w)

%custom calculation of STD and MEAN value from series of values (x)
%selected - matrix of false or true values; a == false correspond to outliers

if nargin < 3
    robustStyle = '1D';
end



if dim == 2
    x = x';
    if nargin == 4
        w = w';
    end
end



N = size(x,2);

selected_isnan = isnan(x);
selected = sum(selected_isnan,2) == 0;
selected0 = not(selected);

while sum(selected ~= selected0) > 0

    if nargin < 4 % if weights are not defined

        MEAN = mean(x(selected,:),1); 
        STD = std(x(selected,:),1,1); 

    else

        MEAN = sum(x(selected,:).*w(selected,:),1)/sum(w(selected,:),1); 
        STD = sqrt(...
            sum(w(selected,:).*(x(selected,:) - MEAN).^2,1)./ ...
            sum(w(selected,:),1));

    end

    selected0 = selected;

    if strcmp(robustStyle,'1D')
        R = abs((x - MEAN)./STD/3);
        selected = R < 1;
        selected = sum(selected,2) == N;
    elseif strcmp(robustStyle,'multiD')
        R = sum(((x(selected,:) - MEAN)./STD/3).^2,2);
        selected(selected) = R < 1;
    end
end

if dim == 2
    STD = STD';
    MEAN = MEAN';
    selected = selected';
end

return


%custom calculation of STD and MEAN value from series of values (x)
%selected - matrix of false or true values; a == false correspond to outliers

if dim == 2
    x = x';
end

if nargin < 3
    robustStyle = '1D';
end

N = size(x,2);

selected_isnan = isnan(x);

selected = sum(selected_isnan,2) == 0;
MEAN = mean(x(selected,:),1); 
STD = std(x(selected,:),1,1); 

selected0 = ~selected;

while sum(selected) < sum(selected0)
    MEAN = mean(x(selected,:),1); 
    STD = std(x(selected,:),1,1); 
    selected0 = selected;
    if strcmp(robustStyle,'1D')
        R = abs((x - MEAN)./STD/3);
        selected = R < 1;
        selected = sum(selected,2) == N;
    else
        R = sum(((x(selected,:) - MEAN)./STD/3).^2,2);
        selected(selected) = R < 1;
    end
end

if dim == 2
    STD = STD';
    MEAN = MEAN';
    selected = selected';
end
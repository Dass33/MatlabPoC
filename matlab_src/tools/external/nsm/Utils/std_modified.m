function [STD, MEAN, selected] = std_modified (x, fun_mean, fun_stabil)

%custom calculation of STD and MEAN value from series of values (x)
%a - matrix of false or true values; a == false correspond to outliers

%fun_mean = 0 or 1;  
%   fun_mean = 0 - mean is expected to be zero
%   fun_mean = 1 - mean is calculated
%fun_stabil = 0 or 1
%   fun_stabil = 0 - involves all the x values
%   fun_stabil = 1 -  cut out the ouliers which distance from mean is too high, abs(x - MEAN) > 3*STD 
%   fun_stabil = 2 - cut out outliers that are much higher than the mean,  x - MEAN > 3*STD

selected_isnan = isnan(x);

if fun_mean == 0  %mean is expected to be zero
    
    selected = not(selected_isnan);
    STD = sqrt(sum(x(selected).^2)/(length(x(selected))-1));
    MEAN = 0;

    if fun_stabil == 1 % cut out the ouliers

        selected0 = not(selected_isnan);
        selected = abs(x) < 3*STD; 
        while sum(selected) < sum(selected0)
            STD = sqrt(sum(x(selected).^2)/(sum(selected)-1));
            selected0 = selected;
            selected = abs(x) < 3*STD;
        end
    end
    
elseif fun_mean == 1  %mean is calculated
    
    selected = not(selected_isnan);
    MEAN = mean(x(selected));
    STD  = sqrt(sum((x(selected) - MEAN).^2)/(length(x(selected))-1));
    
    
    if fun_stabil==1 
        
        selected0 = not(selected_isnan);
        selected = abs(x - MEAN) < 3*STD; 
        while sum(selected) < sum(selected0)
            MEAN = mean(x(selected));
            STD = sqrt(sum((x(selected) - MEAN).^2)/(sum(selected)-1));
            selected0 = selected;
            selected = abs(x - MEAN) < 3*STD;
        end

    elseif fun_stabil==2 
        
        selected0 = not(selected_isnan);
        selected = x - MEAN < 3*STD; 
        while sum(selected) < sum(selected0)
            MEAN = mean(x(selected));
            STD = sqrt(sum((x(selected) - MEAN).^2)/(sum(selected)-1));
            selected0 = selected;
            selected = x - MEAN < 3*STD;
        end

    end
    
end
            
    
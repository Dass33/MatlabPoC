function [STD,MEAN] = std_weighted(x)

%custom calculation of STD and MEAN value from series of values (x) with
%weights (w)
%a - matrix of false or true values; a == false correspond to outliers

%fun_mean = 0 or 1;  
%   fun_mean = 0 - mean is expected to be zero
%   fun_mean = 1 - mean is calculated
%fun_stabil = 0 or 1
%   fun_stabil = 0 - involves all the x values
%   fun_stabil = 1 -  cut out the ouliers
%   fun_stabil = 2 - variance defined weights

% aisnan = isnan(x)==0;
% x=x(aisnan);
% 
% if fun_mean==0  %mean is expected to be zero
% 
%     MEAN = 0;
%     DISTANCE = x - MEAN;
%     STD = sqrt(sum(DISTANCE.^2.*w)./((length(w)-1)/length(w)*sum(w.^2)));
%     a = aisnan;
% 
%     if fun_stabil == 1
%         disp('std_weigthed: not finished!'); return
%     end
% 
% elseif fun_mean==1

    precision = 0.1;
    maxIterationSteps = 100;

    MEAN = mean(x);
    STD = std(x,1);
    A = Inf;
    kk = 0;
    
    while A > precision && kk < maxIterationSteps

        kk = kk + 1;

        w = exp(-0.5*((x-MEAN)./STD).^2);
        MEAN0 = MEAN;
        MEAN = sum(x.*w)/sum(w);
        DISTANCE = x - MEAN;
        STD = sqrt(sum(DISTANCE.^2.*w)./sum(w));
        A = abs(MEAN-MEAN0)/STD;
    end

    if kk == maxIterationSteps
        disp('std_weighted: not converged')
    end

% end





function [M,SD,Cx] = mean_removing_outliers(X, RMZEROVALS)
% 
% [M,SD,Cx] = mean_removing_outliers(X,RMZEROVALS)
% 
% Compute the (non-parametric) robust mean (M) and the standard deviation (SD) 
% of a given vector or matrix (X). The resulting values are considered robust as they are 
% computed ITERATIVELY removing those observations that are classified as outliers. 
% Instead of using the classical "Tukey's Boxplot" method (where observation Xi 
% is considered outlier if Xi < Q1 - 1.5·IQR or Xi > Q3 + 1.5·IQR), this algorithm uses a slightly 
%  different method to detect outliers. Here, Xi is considered an outlier if   
%  Xi < Q1 - 1.5*(Q2-Q1) or Xi > Q3 + 1.5*(Q3-Q2). This method is more conservative 
%  (as the interval containing valid observations is in general narrower than 
%  that defined by Tukey's method, thus usually leading to a bigger no. of 
%  detected outliers) but at the same time it is more "tailored" on the actual 
%  empirical distribution. 
%  NOTE: NaN values are excluded from the computation.
%  
%  INPUT 
%  
%         X           :  vector
%         RMZEROVALS  :  if '1', zero values are removed from the
%                        computation. default RMZEROVALS is 0, meaning that
%                        zero values are used in the computation.
%         
%  OUTPUT 
%  
%         M           : Robust mean (i.e. computed after outliers removal)
%         SD          : Robust Standard Deviation (i.e. computed after outliers removal)
%         Cx          : vector of the conserved (i.e. non-outliers) observations
%
%                                    
% Ruggero G. Bettinardi
% ---------------------------------------------------------------------------
% Cite As:
% Ruggero G. Bettinardi (2025). mean_removing_outliers(X, RMZEROVALS) (https://ch.mathworks.com/matlabcentral/fileexchange/62953-mean_removing_outliers-x-rmzerovals), MATLAB Central File Exchange. Retrieved October 21, 2025.

if nargin < 2
    RMZEROVALS = 0;
end

if RMZEROVALS == 0
    x = X;
else
    X(X==0) = nan;
    x       = X; 
end

if size(x,1) == 1
    x = x';
end

n   = numel(x);  % no. of observations
aux = nan(n,1);  % useful for while-loop

while ~isempty(aux)
    
    x = x(ismember(x,aux)==0);
    
    Q1   = prctile(x,25);     % 1st quartile
    Q2   = prctile(x,50);     % 2nd quartile (median)
    Q3   = prctile(x,75);     % 3rd quartile
    lb   = Q1 - 1.5*(Q2-Q1);  % define lower boundary
    ub   = Q3 + 1.5*(Q3-Q2);  % define lower boundary    
    L   = x(x < lb);          % extract observations below lower boundary
    U   = x(x > ub);          % extract observations above upper boundary
    aux = cat(1,U,L);         % update aux
    
end

Cx = x;
M  = nanmean(x);
SD = nanstd(x);














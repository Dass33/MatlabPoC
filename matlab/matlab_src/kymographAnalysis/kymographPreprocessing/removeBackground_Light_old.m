function [C, result] = removeBackground_Light_old(R, params, Mask)

% Related to the two-pass kymograph reconstruction (implements Sections 4 in the documentation)
% Specifically - estimation of particle contrast (C) and residual opticla
% profile drift (epsilon) from residual field (R)

% Input: 
% - R: Residual, Nt x Nx matrix
% - params: struct with algorithm parameters 
% - Mask: Nt x Nx matrix which elements are 'false' for pixels and frames that contain particle's image, and 'true' elsewhere.

% Output: result, result.C_filtr = final contrast map (Nt x Nx), and various intermediate fields
%  .C, .epsilon 

%% if Mask provided, exchange the false elements from the Mask to NaN values in R
RMasked = R;
if nargin == 3
    RMasked(not(Mask)) = NaN;
end

%% Estimate epsilon_x 
if strcmp(params.analysis.removeBackground_Light_averageX, 'mean') 
    % Estimate epsilon_x using time averaging
    if strcmp(params.analysis.removeBackground_Light_maskX, 'on')
        Ex = movmean(RMasked, 2*params.Wx + 1, 2);
        Ex = interpolateNaNs(Ex, 2);
    else
        Ex = movmean(R, 2*params.Wx + 1, 2);
    end
elseif strcmp(params.analysis.removeBackground_Light_averageX, 'median') 
    % Estimate epsilon_x using time averaging
    Ex = movmedian(RMasked, 2*params.Wx + 1, 2);    
end

    


%% Estimate epsilon_t 
if strcmp(params.analysis.removeBackground_Light_averageT, 'mean') 
    % Estimate epsilon_t using spatial averaging
    if strcmp(params.analysis.removeBackground_Light_maskT, 'on')  
        Et = movmean(RMasked./Ex, 2*params.Wt + 1, 1);
        Et = interpolateNaNs(Et, 1);
    else
        Et = movmean(R./Ex, 2*params.Wt + 1, 1);
    end
elseif strcmp(params.analysis.removeBackground_Light_averageT, 'median') 
    % Estimate epsilon_t using spatial averaging
    Et = movmedian(RMasked./Ex, 2*params.Wt + 1, 1);    
end



%% calculate epsilon
epsilon = Ex.*Et;

%% Calculate particle contrast C
C = R./epsilon - 1;
   
%% Package results
result.C = C;
result.epsilon = epsilon;


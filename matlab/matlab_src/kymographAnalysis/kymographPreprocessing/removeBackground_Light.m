function [C, result] = removeBackground_Light(I, params, Mask)

% Related to the two-pass kymograph reconstruction (implements Sections 4 in the documentation)
% Specifically - estimation of particle contrast (C) and residual opticla
% profile drift (epsilon) from residual field (R)

% Input: 
% - R: Residual, Nt x Nx matrix
% - params: struct with algorithm parameters 
% - Mask: Nt x Nx matrix which elements are 'false' for pixels and frames that contain particle's image, and 'true' elsewhere.

% Output: result, result.C_filtr = final contrast map (Nt x Nx), and various intermediate fields
%  .C, .epsilon 

[Nt, Nx] = size(I);
threshold = 1e-4;

%% if Mask provided, exchange the false elements from the Mask to NaN values in R
IMasked = I;
if nargin == 3
    IMasked(not(Mask)) = NaN;
else
    Mask = true(Nt, Nx);
end

%%%%% this works but I have just ptemporarily omitted that!!
b_t = ones(Nt,1);
R0 = Inf(Nt,Nx);
R = ones(Nt, Nx);
while sum(abs(R0 - R) > threshold) > 0

    R0 = R;
    b_x = mean(IMasked./b_t,1,'omitnan');
    b_t = mean(IMasked./b_x,2,'omitnan');
    R = I./b_x./b_t;
end
%%%%%
% R = I;
% IMasked = IMasked;


RMasked = R;
if nargin == 3
    RMasked(not(Mask)) = NaN;

    % [x1,t1] = meshgrid(1:Nx, 1:Nt);
    % t0 = t1(Mask);
    % x0 = x1(Mask);
    % R0 = R(Mask);
    % 
    % RMasked = griddata(x0,t0,R0,x1,t1);

end

%%%%% this works
epsilon_t = ones(Nt, Nx);
epsilon_x = ones(Nt, Nx);
C0 = Inf(Nt,Nx);
C = ones(Nt, Nx);
kk = 0;
while sum(abs(C0 - C) > threshold, 'all') > 0 && kk < 50

    C0 = C;
    kk = kk+1;

    if strcmp(params.analysis.removeBackground_Light_maskX, 'on')
        epsilon_t = movmean(RMasked./epsilon_x, 2*params.Wx + 1, 2);
        epsilon_t = interpolateNaNs(epsilon_t,2);
    else
        epsilon_t = movmean(R./epsilon_x, 2*params.Wx + 1, 2);
    end


    if strcmp(params.analysis.removeBackground_Light_maskT, 'on')
        epsilon_x = movmean(RMasked./epsilon_t, 2*params.Wt + 1, 1);
        epsilon_x = interpolateNaNs(epsilon_x,1);
    else
        epsilon_x = movmean(R./epsilon_t, 2*params.Wt + 1, 1);
    end

    C = R./epsilon_x./epsilon_t;

end
if sum(abs(C0 - C) > threshold) > 0
    disp('removeBeackground_light: did not converge')
end
%%%%%%



C = C - 1;

% epsilon_t = ones(Nt, Nx);
% C0 = Inf(Nt,Nx);
% C = ones(Nt, Nx);
% while sum(abs(C0 - C) > threshold) > 0
% 
%     C0 = C;
%     epsilon_x = movmean(IMasked./epsilon_t,2*params.Wt + 1, 1,'omitnan');
%     epsilon_t = movmean(IMasked./epsilon_x,2*params.Wx + 1, 2,'omitnan');
%     C = I./epsilon_x./epsilon_t;
% 
% end
% 
% C = C - 1;

   
%% Package results
result.C = C;
result.epsilon_x = epsilon_x;
result.epsilon_t = epsilon_t;


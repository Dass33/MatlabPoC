function [R, result] = removeBackground_Dark(I, params, Mask)

% Related to the two-pass kymograph reconstruction (implements Sections 4 in the documentation)
% Specifically - estimation of optical (B) and dark background (D) from measured intesity (I) 

% Input: 
% - I (Nt x Nx) measured intensity (cols = spatial pixels, rows = frames)
% - Mask: Nt x Nx matrix which elements are 'false' for pixels and frames that contain particle's image, and 'true' elsewhere.
% - params.analysis.removeBackground_param1: defines different strategy to estimate b_x
%       'global b_x' - <this in the only one that is finished at the this moment>
%
% Output: result, result.C_filtr = final contrast map (Nt x Nx), and various intermediate fields
%  .b_x, .b_t, .d_t, .B, .D_t, .R, .A

%% sizes
[Nt, Nx] = size(I);

%% if Mask provided, exchange the false elements from the Mask to NaN values in I
IMasked = I;
if nargin == 3
    IMasked(not(Mask)) = NaN;
else
    Mask = true([Nt, Nx]);
end

%% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
A = zeros(16, Nx);
for i = 1:16
    A(i,i:16:end) = 1;
end

if strcmp(params.analysis.removeBackground_Dark, 'global b_x')

    %% Calculate b_x
    b_x = mean(IMasked,1,'omitnan');
    
    %% For each frame t solve linear system: I(t,:) = b_x*b_t(t,:) + A * d_t(t,:)
    % Unknown vector p = [b_t(t); d_t(t,:)] length 17
    
    b_t = ones(Nt, 1);
    d_t = ones(Nt, 16);
    for i = 1:Nt
         s = linsolve([b_x(Mask(i,:))',A(:, Mask(i,:))'], IMasked(i,Mask(i,:))');
         b_t(i) = s(1)';
         d_t(i,:) = s(2:end)';
    end

    %% Reconstruct background fields B and D
    B = b_x.*b_t;     
    D_t = d_t*A;  

% elseif strcmp(params.analysis.removeBackground_param1, 'local in time b_x')
% 
%     %% Calculate b_x
%     b_x = movmean(IMasked,2*params.Wt + 1,1,'omitnan');
% 
%     %% For each frame t solve linear system: I(t,:) = b_x*b_t(t,:) + A * d_t(t,:)
%     % Unknown vector p = [b_t(t); d_t(t,:)] length 17
% 
%     b_t = ones(Nt, 1);
%     d0_t = ones(Nt, 16);
%     for i = 1:Nt
%          s = linsolve([b_x(i,Mask(i,:))',A(:, Mask(i,:))'], IMasked(i,Mask(i,:))');
%          b_t(i) = s(1)';
%          d0_t(i,:) = s(2:end)';
%     end
% 
%     %% calculate d_t, d*Z = d0_t
%     % contruct matrix Z
%     Z0 = eye(Nt, Nt);
%     Z = Z0 - imdilate(Z0,ones(1, 2*params.Wt + 1))/(2*params.Wt + 1);
%     % solve equation
%     d_t = ones(Nt, 16);
%     for i = 1:16
%         d_t(:,i) = linsolve(Z, d0_t(:,i));
%     end
%     d_t = d0_t;
% 
%     %% Reconstruct background fields B and D
%     B = b_x.*b_t;     
%     D_t = d_t*A;

elseif strcmp(params.analysis.removeBackground_Dark, 'local in space b_x')

    %% Calculate b_x
    b_x = mean(IMasked,1,'omitnan');
    
    %% For each frame t solve linear system: I(t,:) = b_x*b_t(t,:) + A * d_t(t,:)
    % Unknown vector p = [b_t(t); d_t(t,:)] length 17

    % prepare coeeficents for solving linear system
    b_x0 = b_x';
    b_x0 = repmat(b_x0, 1, Nx/16);
    % matrix c
    C = zeros(size(b_x0));
    for i = 1:Nx/16
        C((i-1)*16+1:i*16,i) = 1;
    end
    b_x0 = b_x0.*C;
    A0 = A';
    IMasked0 = IMasked';

    b_t = ones(Nx/16, Nt);
    d_t = ones(16, Nt);

    for i = 1:Nt
         s = linsolve([b_x0(Mask(i,:),:),A0(Mask(i,:),:)], IMasked0(Mask(i,:),i));
         b_t(:,i) = s(1:Nx/16);
         d_t(:,i) = s(Nx/16+1:end);
    end 
    b_t = b_t';
    d_t = d_t';
    b_x0 = b_x0';
    
    B = 1;
    D_t = d_t*A;
    
    % %B = b_t*b_x0;     
    % D_t = d_t*A;
    % 
    % b_t = mean((IMasked - D_t)./b_x,2,'omitnan');
    % 
    % B  = b_t;%*b_x; 

elseif strcmp(params.analysis.removeBackground_Dark, 'local in time b_x')  

    W = repmat(sqrt(mean(I,1,'omitnan')), Nt-1,1);
    W(not(Mask(1:end-1,:)) | not(Mask(2:end,:))) = 0;
    b = ones(Nt,1);
    d = zeros(Nt,16);
    for i = 1:Nt-1

         s = weighted_multireg(I(i,:)', A', I(i+1,:)', W(i,:)');
         b(i+1) = s(1);
         d(i,:) = s(2:end)';

    end

    d_t = cumsum(d);
    %d_t = d_t/sum(d_t);
    b_t = cumprod(b);

    %% Calculate b_x
    b_x = movmean(IMasked,2*params.Wt + 1,1,'omitnan');

    %% Reconstruct background fields B and D
    B = b_t;     
    D_t = d_t*A;

elseif strcmp(params.analysis.removeBackground_Dark, 'test1')  

    W = repmat(sqrt(mean(I,1,'omitnan')), Nt-1,1);
    A1 = x;
    b = ones(Nt,1);
    d = zeros(Nt,16);
    for i = 1:Nt-1

         s = weighted_multireg(I(i,:)', A1', I(i+1,:)', W(i,:)');
         b(i+1) = s(1);
         d(i,:) = s(2:end)';

    end

    d_t = cumsum(d);
    %d_t = d_t/sum(d_t);
    b_t = cumprod(b);

    %% Calculate b_x
    b_x = movmean(IMasked,2*params.Wt + 1,1,'omitnan');

    %% Reconstruct background fields B and D
    B = b_t;     
    D_t = d_t*A;    

elseif strcmp(params.analysis.removeBackground_Dark, 'test')  


    % matrix c
    C1 = zeros(Nx,Nx/16);
    for i = 1:Nx/16
        C1((i-1)*16+1:i*16,i) = 1;
    end
    
    C2 = zeros(Nx,Nx/16-1);
    for i = 1:Nx/16-1
        C2((i-1)*16+9:i*16+8,i) = 1;
    end
    

    b1_t = ones(Nt, Nx/16);
    d1_t = zeros(Nt, 16);
    b2_t = ones(Nt, Nx/16-1);
    d2_t = zeros(Nt, 16);
    for i = 1:Nt-1

        II = repmat(I(i,:), Nx/16,1);

         s = linsolve([II'.*C1,A'], I(i+1,:)');
         b1_t(i+1,:) = s(1:Nx/16)';
         d1_t(i+1,:) = s(Nx/16+1:end)';

         II = repmat(I(i,:), Nx/16-1,1);

         s = linsolve([II'.*C2,A'], I(i+1,:)');
         b2_t(i+1,:) = s(1:Nx/16-1)';
         d2_t(i+1,:) = s(Nx/16:end)';
    end

    d_t = cumsum(d);
    %d_t = d_t/sum(d_t);
    b_t = cumprod(b);

    %% Calculate b_x
    b_x = movmean(IMasked,2*params.Wt + 1,1,'omitnan');

    %% Reconstruct background fields B and D
    B = b_t;     
    D_t = d_t*A;    

elseif strcmp(params.analysis.removeBackground_Dark, 'none')  

    D_t = 0;
    B = 1;
    b_x = NaN;
    b_t = NaN;
    A = NaN;
    d_t = NaN;

end   

%% Calculate residual R
R = (I - D_t)./B;    

%% Package results
result.b_x = b_x;
result.b_t = b_t;
result.d_t = d_t;
result.B = B;
result.D_t = D_t;
result.R = R;
result.A = A;


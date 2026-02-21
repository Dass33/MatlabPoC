function A = interpolateNaNs(A, dim)

% this function interpolates matrix A at its NaN values. at the edges, it
% intepolates along the other dimenaion values that has been averaged (by movmean with sliding window size W) 
% input:
% - A - matrix to interpolate
% - dim - dimension in which the interpolation should take place
% - W - size of the sliding window for interpolation at the edges

%flip temporarily the dimesions for option dim = 1
if dim == 1
    A = A';
end

Mask = isnan(A);
if sum(Mask,'all') > 0

    % sizes
    [Nt, Nx] = size(A);
    x = 1:Nx;
    %t = (1:Nt)';

    %inverse Mask
    notMask = not(Mask);

    % %interpolate at the first pixel along the time dimension
    % i = 1;
    % if sum(Mask(:,i)) > 1
    % 
    %     A1 = movmean(A(:,i), W, 1);
    %     Mask1 = isnan(A1);
    %     notMask1 = not(Mask1);
    % 
    %     A(Mask(:,i),i) = interp1(t(notMask1), A1(notMask1,1), t(Mask(:,i)), 'linear');
    %     Mask(:,i) = false;
    %     notMask(:,i) = true;
    % 
    % end
    % 
    % %interpolate at the last pixel along the time dimension
    % i = Nx;
    % if sum(Mask(:,i)) > 1
    % 
    %     A1 = movmean(A(:,i), W, 1);
    %     Mask1 = isnan(A1);
    %     notMask1 = not(Mask1);
    % 
    %     A(Mask(:,i),i) = interp1(t(notMask1), A1(notMask1,1), t(Mask(:,i)), 'linear');
    %     Mask(:,i) = false;
    %     notMask(:,i) = true;
    % 
    % end

    %interpolate along the space dimension 
    sMask = sum(Mask,2);
    for i = 1:Nt
        if sMask(i) > 0 && sMask(i) < Nx-1
            A(i, Mask(i,:)) = interp1(x(notMask(i,:)), A(i,notMask(i,:),1), x(Mask(i,:)), 'linear', 'extrap');
        end
    
    end

end

%flip back the dimesions for option dim = 1
if dim == 1
    A = A';
end

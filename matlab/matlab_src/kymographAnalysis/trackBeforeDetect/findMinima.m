function DIPS = findMinima(Y, Yav)

% finds local minima and determines their properties 
% The local minimum selection is implemented as a grayscale dilation (Jain, 1986) followed by the selection of all pixels that have the same value before and after the dilation.

% input:
% Y - matrix of intensities
% Yav - number of elements for dilation [px], i.e. found minimum is a local minimum within the neighboring Yav pixels
 
% output:
% DIPS.timeFrame - serie of frames correspondng to local minimas [frame]
% DIPS.position - serie of positions [px]
% DIPS.positionRefined - series of refined positions [px], calculated as position of centroid  
% DIPS.I - series of intensities at local minimas 
% DIPS.I_noise - noise at DIPS.position
% DIPS.I_norm - series of relative intensities compared to the noise level

%% local minimun selection
Yt = transpose(-Y); 
sYt = size(Yt);

Mask=ones(Yav,1); Mask((Yav+1)/2)=0;
B = imdilate(Yt,Mask);
ind = find(Yt > B);

if isempty(ind) == 0

    [sub1,sub2] = ind2sub(size(Yt),ind);
    % a = sub1 >= (Yav+1)/2 & sub1 <= size(Y,2) - (Yav+1)/2;
    % ind = ind(a);
    % sub1 = sub1(a); %position of DIPS
    % sub2 = sub2(a); %timeFrame of DIPS

    DIPS.position = sub1;
    DIPS.timeFrame = sub2;
    DIPS.I = -Yt(ind);
    
    %% position refinement procedure
    m0 = conv2(Yt,ones(Yav,1),'same');
    X = (1:size(Y,2))';
    m1 = conv2(Yt.*X,ones(Yav,1),'same')./m0;
    m1_difference=abs(X-m1);

    sub1_shift = -(Yav-1)/2 : (Yav-1)/2;
    sub1_a = repmat(sub1,1,length(sub1_shift)) + repmat(sub1_shift,length(sub1),1);
    sub1_a(sub1_a < 1) = 1;
    sub1_a(sub1_a > sYt(1)) = sYt(1);
    sub2_a = repmat(sub2,1,length(sub1_shift));
    ind_a = sub2ind(size(Yt), sub1_a, sub2_a);
    m1_difference_a = m1_difference(ind_a);
    [~,a] = min(m1_difference_a,[],2);

    sub1_refined = sub1 + a - (Yav+1)/2;
    sub1_refined(sub1_refined < 1) = 1;
    sub1_refined(sub1_refined > sYt(1)) = sYt(1);
    ind_refined = sub2ind(size(Yt), sub1_refined, sub2);

    DIPS.positionRefined = m1(ind_refined);

    %% noise level at the position of dips
    I_std = STD_profile(Y);
    DIPS.I_noise = I_std(DIPS.position); 
    DIPS.I_noise = DIPS.I_noise(:); 
    DIPS.I_norm = DIPS.I./DIPS.I_noise;

else

    DIPS.timeFrame = []; 
    DIPS.position = [];
    DIPS.positionRefined = [];
    DIPS.I = []; 
    DIPS.I_noise = [];
    DIPS.I_norm = [];

end

DIPS.sI = [sYt(2), sYt(1)];






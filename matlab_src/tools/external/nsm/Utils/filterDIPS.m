function DIPS = filterDIPS(DIPS0, I0, I, A, threshold)

%A - length of the temporal window from which the STD is calculated
%threshold - threshold value of STD above which the DIPS will be discarded

%STD0 = std_modified (I(I>0), 0, 1);
% bit_depth = 255;
% well_depth = 15000;
% STD_expected = 1/sqrt(mean(I0(:))*bit_depth/well_depth*66*8);

%% calculated modified STD for each time step
STD = Inf*ones(1,size(I,1));
for i=A+1:size(I,1)-A
        B = I(i-A:i+A,:);
        STD(i) = std_modified (B(:), 0, 1);
end

%% filter timeframes which did not make it through threshold
a = STD(DIPS0.timeFrame) < threshold*min(STD);

fnames = fieldnames(DIPS0);
for i=1:length(fnames)
    if strcmp(fnames{i},'indTS') == 0 & strcmp(fnames{i},'ind') == 0
        DIPS.(fnames{i}) = DIPS0.(fnames{i})(a);
    end
end

%% time sorted indexes 
DIPS.indTS = cell(1,size(I,1));
DIPS.ind = zeros(size(I,1),1);
for i=1:length(DIPS.timeFrame)
    DIPS.indTS{DIPS.timeFrame(i)} = [DIPS.indTS{DIPS.timeFrame(i)}, i];
    DIPS.ind(i) = length(DIPS.indTS{DIPS.timeFrame(i)});
end


%disp('')
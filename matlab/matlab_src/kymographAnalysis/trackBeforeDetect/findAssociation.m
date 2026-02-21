function [DIPSCOMB, DIPS,COMB] = findAssociation (DIPS, PT_setting, Image)

%% add DUMMY (DUMMY at position0 for all timeFrames; at position DIPS.sI(2)+1 for all timeFrames; 2x at NaN position at timeFrame NaN (second one means the combintion is repeating)
DIPS.isDUMMY = [false(length(DIPS.timeFrame),1); true(2*DIPS.sI(1)+2,1)];
DIPS.timeFrame = [DIPS.timeFrame; (1:DIPS.sI(1))'; (1:DIPS.sI(1))'; NaN; NaN];
DIPS.position = [DIPS.position; zeros(DIPS.sI(1),1); (DIPS.sI(2)+1)*ones(DIPS.sI(1),1); NaN; NaN];
DIPS.I = [DIPS.I; NaN(2*DIPS.sI(1),1); NaN; NaN];
DIPS.I_noise = [DIPS.I_noise; NaN(2*DIPS.sI(1),1); NaN; NaN];
DIPS.I_norm = [DIPS.I_norm; NaN(2*DIPS.sI(1),1); NaN; NaN];
DIPS.positionRefined = [DIPS.positionRefined; zeros(DIPS.sI(1),1); (DIPS.sI(2)+1)*ones(DIPS.sI(1),1); NaN; NaN];
noDIPS = length(DIPS.timeFrame);
noDUMMY2 = noDIPS;

%% time sorted indexes 
DIPS.indTS = cell(1, DIPS.sI(1));
for i=1:length(DIPS.timeFrame)-2
    DIPS.indTS{DIPS.timeFrame(i)} = [DIPS.indTS{DIPS.timeFrame(i)}, i];
end

%% connections to neighboring frames in next frame
COMB = [(noDUMMY2-1)*ones(noDIPS,1), noDUMMY2*ones(noDIPS,1)];
COMB(end,1) = noDUMMY2;

for it=1:DIPS.sI(1)-1

    if isempty(DIPS.indTS{it}) == 0 && isempty(DIPS.indTS{it+1}) == 0

        position1=DIPS.positionRefined(DIPS.indTS{it});
        position2=DIPS.positionRefined(DIPS.indTS{it+1});
        Dx = abs(repmat(position1,1,length(position2)) - repmat(position2',length(position1),1) + PT_setting.flowEstimate);

        %first distance minimum
        [a,b] = min(Dx,[],2);
        COMB(DIPS.indTS{it},1) = DIPS.indTS{it+1}(b);

        %second distance minimum
        b = sub2ind(size(Dx),[1:size(Dx,1)]',b);
        Dx(b) = Inf;
        [a,b] = min(Dx,[],2);
        COMB(DIPS.indTS{it},2) = DIPS.indTS{it+1}(b);

    end
end

%% all combination in 2 frames
a = permute(1:noDIPS, [3,1,2]);
a = repmat(a,1,2,1);
b = permute(COMB, [3, 2, 1]);
DIPSCOMB.ind = [a;b];


if PT_setting.Tlength  == 2

    I = DIPS.I_norm(DIPSCOMB.ind);
    DIPSCOMB.I = mean(I,1, 'omitnan');
    DIPSCOMB.Istd = abs(diff(I),1);
    position = DIPS.positionRefined(DIPSCOMB.ind);
    DIPSCOMB.D = abs(diff(position,1,1) - PT_setting.flowEstimate);
    
end

%% all combination in Tlength frames
Tlength = 2;
isDUMMY = DIPS.isDUMMY(DIPSCOMB.ind);
relevantToExtend = sum(not(isDUMMY(end,:,:)),2) > 0;

while Tlength < PT_setting.Tlength && sum(relevantToExtend) > 0 

    % create all possible combination (only for those that are still relevant to extend)

    DIPSCOMB0.ind = DIPSCOMB.ind(:,:,relevantToExtend);
    noDIPS0 = size(DIPSCOMB0.ind, 3);
    a = DIPSCOMB0.ind(end,:,:);

    b1 = COMB(a,1);
    b1 = reshape(b1, [], noDIPS0);
    b2 = COMB(a,2);
    b2 = reshape(b2, [], noDIPS0);
    b = [b1;b2];

    c = DIPSCOMB.ind(:,:,b);
    c = reshape(c, size(c,1), [], noDIPS0);

    d = repmat(DIPSCOMB0.ind, size(c,2)/size(DIPSCOMB0.ind,2)/2, 1, 1);
    d = reshape(d, size(c,1), size(c,2)/2, size(c,3));
    d = repmat(d,1,2,1);
    
    DIPSCOMB0.ind = [d; c];
    Tlength = 2*Tlength;    


    % filter associations
    if size(DIPSCOMB0.ind,2) > PT_setting.TmaxNo %|| Tlength == PT_setting.Tlength 

        %%evaluate association
        DIPSCOMB0 = evaluateDIPSCOMB(DIPS, DIPSCOMB0);

        %%reduce the number of associations

        I = DIPSCOMB0.I;
        Istd = DIPSCOMB0.Istd;
        D = DIPSCOMB0.D;
        N = DIPSCOMB0.N;

        %calculate COST
        COST_I = I - min(I,[],2);
        COST_I = COST_I./max(COST_I,[],2);

        COST_Istd = Istd - min(Istd, [], 2);
        COST_Istd = COST_Istd./max(COST_Istd,[],2);

        COST_D = D - min(D, [], 2);
        COST_D = COST_D./max(COST_D,[],2);

        COST_N = N - min(N, [], 2);
        COST_N = COST_N./max(COST_N,[],2);

        COST = COST_I.^2 + COST_Istd.^2 + COST_D.^2 + COST_N.^2;

        %select based on minimal COST
        [~, sub20] = sort(COST,2);
        sub20 = sub20(:, 1:PT_setting.TmaxNo,:);
        sub2 = repmat(sub20, Tlength, 1, 1);
        sub1 = repmat((1:Tlength)', 1, size(sub2,2), size(sub2,3));
        sub3 = permute(1:noDIPS0, [3,1,2]);
        sub3 = repmat(sub3, Tlength, size(sub2,2), 1);
        ind = sub2ind(size(DIPSCOMB0.ind), sub1, sub2, sub3);

        DIPSCOMB0.ind = DIPSCOMB0.ind(ind);

    end

    % close all
    % imagesc(Image); hold on
    % a = 500;
    % plot(DIPS.position(DIPSCOMB.ind(:,:,a)), DIPS.timeFrame(DIPSCOMB.ind(:,:,a)), 'Marker','.','Color','white')
    % ylim([DIPS.timeFrame(a) - 5, DIPS.timeFrame(a) + 5 + Tlength])

    % combine everyone (relevant and irelevant to extend)
    a = DIPSCOMB.ind(:,:,not(relevantToExtend));
    a = [a; repmat(a(end,:,:), size(a,1), 1, 1)];
    a = [a, noDUMMY2*ones(size(a,1), size(DIPSCOMB0.ind,2) - size(a,2), size(a,3))];

    DIPSCOMB.ind = noDUMMY2*ones(size(DIPSCOMB0.ind,1), size(DIPSCOMB0.ind,2), noDIPS);
    DIPSCOMB.ind(:,:,relevantToExtend) = DIPSCOMB0.ind;
    
    DIPSCOMB.ind(:,:,not(relevantToExtend)) = a;

    % evaluate which is relevant to extend
    isDUMMY = DIPS.isDUMMY(DIPSCOMB.ind);
    relevantToExtend = sum(not(isDUMMY(end,:,:)),2) > 0;

    %disp(strcat('findAssociation: Tlength = ', num2str(Tlength), ', number of relevant DIPS to extend:', num2str(sum(relevantToExtend))))

end

% if isnan(ind) 
% 
%     DIPSCOMB.I = I;
%     DIPSCOMB.Istd = Istd;
%     DIPSCOMB.D = D;
% 
% else
% 
%     sub30 = permute(1:noDIPS, [3,1,2]);
%     sub30 = repmat(sub30, 1, size(sub20,2), 1);
%     ind = sub2ind([size(I,2), size(I,3)], sub20, sub30);
% 
%     DIPSCOMB.I = I(ind);
%     DIPSCOMB.Istd = Istd(ind);
%     DIPSCOMB.D = D(ind);
% 
% end





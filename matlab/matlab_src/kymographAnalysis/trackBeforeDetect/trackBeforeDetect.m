function PARTICLES = trackBeforeDetect(I, setting)

plotSubResults = 0;

%% feature point identification
meanRMSWidthAfterDenoising = sqrt(2)*setting.kymographPreprocessing.ws;
meanFWHM = 2*sqrt(2*log(2))* meanRMSWidthAfterDenoising;
Wm = floor((meanFWHM - 1)/2)*2+1; %minimal distance between spots, must be odd

    DIPS = findMinima(I, Wm);

    if plotSubResults == 1
        %%
        figure
        imagesc(I); hold on
        plot(DIPS.position,DIPS.timeFrame,'.','Color','white')
    end

    %% feature associations 
    %disp('finding DIPSCOMB')
    [DIPSCOMB, DIPS2, COMB] = findAssociation(DIPS, setting, I);
    % if strcmp(setting.TlengthMin, 'entering & leaving FOV') == 1
    %     DIPSCOMB = prolongAssociationOverFOV(DIPS2, DIPSCOMB, COMB, setting, I);
    % end
    DIPSCOMB = evaluateDIPSCOMB(DIPS2, DIPSCOMB);


    if plotSubResults == 1
        %%
        figure
        tt = 100:200;
        a = DIPS2.timeFrame(DIPSCOMB.ind(1,:,:)) <= tt(end) & DIPS2.timeFrame(DIPSCOMB.ind(1,:,:)) >= tt(1);
        imagesc(1:size(I,2),1:size(I,1),I); hold on
        position = DIPS2.position(DIPSCOMB.ind(:,a));
        timeFrame = DIPS2.timeFrame(DIPSCOMB.ind(:,a));

        plot(position, timeFrame,'Marker','.','Color','white')
        ylim([tt(1) tt(end)])

    end

    %% thresholding based on I thresholdlimit 
    fnames = fieldnames(DIPSCOMB);
    for i=1:length(fnames)
        DIPSCOMB_selected.(fnames{i}) = reshape(DIPSCOMB.(fnames{i}), size(DIPSCOMB.(fnames{i}),1), []);
    end

    relevant = DIPSCOMB_selected.I < setting.thresholdLimit;

    for i=1:length(fnames)
        DIPSCOMB_selected.(fnames{i}) = DIPSCOMB_selected.(fnames{i})(:,relevant);
    end

    if plotSubResults == 1
        %%
        figure
        %tt = 1560:1680;
        tt = 1:1000;
        a = DIPS2.timeFrame(DIPSCOMB_selected.ind(1,:)) <= tt(end) & DIPS2.timeFrame(DIPSCOMB_selected.ind(1,:)) >= tt(1);
        imagesc(1:size(I,2),1:size(I,1),I); hold on
        plot(DIPS2.position(DIPSCOMB_selected.ind(:,a)),DIPS2.timeFrame(DIPSCOMB_selected.ind(:,a)),'Marker','.','Color','white')
        ylim([tt(1) tt(end)])
        caxis([-3*std(I(:)) 3*std(I(:))])

    end

    %% linking procedure  
      %disp('linking into trajectory')
      PARTICLES = linking(DIPS2, DIPSCOMB_selected, I);

function [collection, inputDataInfo] = kymographAnalysis(experimentFolder, Setting)

% mh, v1.1, 2026_02_20

%% combination of sweeps
[Setting.kymographPreprocessing.Wx, Setting.kymographPreprocessing.Wt] = meshgrid(...
    Setting.kymographPreprocessing.Wx, Setting.kymographPreprocessing.Wt);

Setting.kymographPreprocessing.Wx = Setting.kymographPreprocessing.Wx(:);
Setting.kymographPreprocessing.Wt = Setting.kymographPreprocessing.Wt(:);
NSweeps = length(Setting.kymographPreprocessing.Wx);

%% list of all raw files
if strcmp(Setting.inputDataFormat, 'mat') == 1
    ExperimentTimeStamp=findXfiles(experimentFolder,'.mat');
else
    ExperimentTimeStamp=findXfiles(experimentFolder,'.tiff');
end

%% create an empty collection
collection = struct;
for j = 1:length(Setting.kymographPreprocessing.Wx)
    for i = 1:length(Setting.kymographAnalysis.trajectoryProperties)
        collection(j).(Setting.kymographAnalysis.trajectoryProperties{i}) = [];
    end
    collection(j).ExperimentTimeStamp = [];
end

%% create names of the sweeps
for i = 1:length(Setting.kymographPreprocessing.Wx)
    collection(i).SweepLegend = strcat('Wx=', num2str(Setting.kymographPreprocessing.Wx(i)),',Wt=', ...
        num2str(Setting.kymographPreprocessing.Wt(i)));
end

%% create folder kymograph
exportKymographFolder = fullfile( Setting.Path.exportFolder,'kymographs');

makeFolderIfNotExisting(exportKymographFolder);

%% run kymograph processing for every file
for itest = 1:length(ExperimentTimeStamp)
    tic

    %% load raw data
    data = loadRawData( fullfile(experimentFolder,ExperimentTimeStamp{itest}), Setting.inputDataFormat);

    if strcmp(Setting.kymographAnalysis.Title, 'OnePassKymographAnalysis')

        [opticalContrast, Trajectory] = OnePassKymographAnalysis(data, ExperimentTimeStamp{itest}, Setting);

    elseif strcmp(Setting.kymographAnalysis.Title, 'TwoPassKymographProcesing')

        [opticalContrast, Trajectory] = TwoPassKymographProcessing(data, Setting);

    end

    for iSweep = 1:NSweeps

        % collect trajectories
        for i = 1:length(Setting.kymographAnalysis.trajectoryProperties)
            collection(iSweep).(Setting.kymographAnalysis.trajectoryProperties{i}) = [collection(iSweep).(Setting.kymographAnalysis.trajectoryProperties{i}), Trajectory(iSweep).(Setting.kymographAnalysis.trajectoryProperties{i})];
        end
        for i = 1:length(Trajectory(iSweep).iOC)
            collection(iSweep).ExperimentTimeStamp{length(collection(iSweep).ExperimentTimeStamp)+1} = ExperimentTimeStamp{itest};
        end

        % plot kymograph
        if strcmp(Setting.kymographAnalysis.plotKymograph, 'on') | ~strcmp(Setting.kymographAnalysis.saveKymograph, 'off')
            close all
            plotKymograph(opticalContrast(:,:,iSweep), Trajectory(iSweep), ...
                strcat(ExperimentTimeStamp{itest},'_',collection(iSweep).SweepLegend))
        end

        % save kymograph
        if ~strcmp(Setting.kymographAnalysis.saveKymograph, 'off')

            % kymographName = [ExperimentTimeStamp{itest},'_',collection(iSweep).SweepLegend];
            kymographName = ExperimentTimeStamp{itest};

            exportgraphics(gcf, fullfile( exportKymographFolder, ...
                [kymographName,'.',Setting.kymographAnalysis.saveKymograph]), ...
                'Resolution',Setting.exportDpi);

        end

        disp(strcat('iSweep:',num2str(iSweep)))

    end

    toc
    disp(strcat(num2str(itest),'/',num2str(length(ExperimentTimeStamp))))

end

%% create inputDataInfo
% length of one frame
inputDataInfo.Dt = data.Dt;

% length of one pixel
inputDataInfo.Dx = data.Dx;

% size of the FOV (in pixels)
inputDataInfo.noPixels = size(data.Im,2);

% temporal length of kymograph (in no of frames)
inputDataInfo.noFrames = size(data.Im,1);







function [collection, inputDataInfo] = OnePassKymographAnalysis(ExperimentFolder, setting)

%% set default setting 


%% combination of sweeps
[setting.kymographPreprocessing.Wx, setting.kymographPreprocessing.Wt] = meshgrid(setting.kymographPreprocessing.Wx, setting.kymographPreprocessing.Wt);
setting.kymographPreprocessing.Wx = setting.kymographPreprocessing.Wx(:);
setting.kymographPreprocessing.Wt = setting.kymographPreprocessing.Wt(:);

%% list of all raw files
if strcmp(setting.inputDataFormat, 'mat') == 1 
    ExperimentTimeStamp=findXfiles(ExperimentFolder,'.mat');
else
    ExperimentTimeStamp=findXfiles(ExperimentFolder,'.tiff');
end

%% create folder collection
d = dir(ExperimentFolder); 
if ~any(strcmp({d.name}, 'collection'))
    mkdir(ExperimentFolder,'collection');
end

%% create an empty collection variable
collection = struct;
for j = 1:length(setting.kymographPreprocessing.Wx)
    for i = 1:length(setting.kymographAnalysis.trajectoryProperties)
        collection(j).(setting.kymographAnalysis.trajectoryProperties{i}) = [];
    end
    collection(j).ExperimentTimeStamp = [];
end

%% add other info to collection (Sweep legend)
% sweeps legend (names)
for i = 1:length(setting.kymographPreprocessing.Wx)
    collection(i).SweepLegend = strcat('Wx=', num2str(setting.kymographPreprocessing.Wx(i)),',Wt=', num2str(setting.kymographPreprocessing.Wt(i)));
end

%% create folder kymograph
if ~strcmp(setting.kymographAnalysis.saveKymograph, 'off')
    d = dir(ExperimentFolder); 
    if ~any(strcmp({d.name}, 'kymographs'))
        mkdir(ExperimentFolder,'kymographs');
    else
        delete(fullfile(ExperimentFolder,'kymographs','*'))
    end
end

%% run kymograph processing for every file
for itest = 1:length(ExperimentTimeStamp)
    tic

    clear data trajectory PARTICLES

    %% load raw data
    data = loadRawData(fullfile(ExperimentFolder,ExperimentTimeStamp{itest}), setting.inputDataFormat);
    
    %% kymograph preprocessing
    opticalContrast = kymographPreprocessing(data, setting.kymographPreprocessing);
    
    %% trajectory detection
    for iSweep = 1:size(opticalContrast,3)
        
        switch setting.trajectoryDetecton.Title
    
            case 'trackBeforeDetect'
    
                Trajectory = trackBeforeDetect(opticalContrast(:,:,iSweep), setting);
    
            case 'gabClosingTracker'
    
                
                Tracks = gabClosingTracker(opticalContrast(:,:,iSweep), ...
                    peakSign=setting.Detection.peakSign,...
                    pfa = setting.Detection.pfa, ...
                    localOptimumRange = setting.Detection.localOptimumRange, ...
                    boarderRange = setting.Detection.boarderRange, ...
                    positionRefinementMethod = setting.FeatureExtraction.positionRefinementMethod, ...
                    fittingRadius = setting.FeatureExtraction.fittingRadius, ...
                    cut_off_distance = setting.Linking.cut_off_distance, ...
                    unmatched_penalty_distance = setting.Linking.unmatched_penalty_distance, ...
                    flowEstimate = setting.Linking.flowEstimate_ums * data.Dt/data.Dx, ...
                    maxPositiveGab = setting.Linking.maxPositiveGab, ...
                    maxNegativeGab = setting.Linking.maxNegativeGab, ...
                    gab_closing_cut_off_distance = setting.Linking.gab_closing_cut_off_distance, ...
                    gab_closing_penalty_distance = setting.Linking.gab_closing_penalty_distance, ...
                    minTrackLength = setting.Linking.minTrackLength);
                

                Trajectory.timeFrame = {};
                Trajectory.position = {};
                Trajectory.positionRefined = {};
                if Tracks.nTracks > 0
                        Trajectory.timeFrame = Tracks.frames;
                        Trajectory.position = Tracks.positions;
                        Trajectory.positionRefined = Tracks.positions_refined;
                end

        end

        % trajectory analysis
        TAsetting.Dt = data.Dt; 
        TAsetting.Dx = data.Dx;
        TAsetting.Wx = setting.kymographPreprocessing.Wx(iSweep);
        %TAsetting.channelArea = setting.channel.area;
        Trajectory = trajectoryAnalysis (Trajectory, setting.kymographAnalysis.trajectoryProperties, TAsetting, opticalContrast(:,:,iSweep));
        Trajectory = rmfield(Trajectory,'position');

       % collect results
       for i = 1:length(setting.kymographAnalysis.trajectoryProperties)
           collection(iSweep).(setting.kymographAnalysis.trajectoryProperties{i}) = [collection(iSweep).(setting.kymographAnalysis.trajectoryProperties{i}), Trajectory.(setting.kymographAnalysis.trajectoryProperties{i})];
       end
       for i = 1:length(Trajectory.iOC)
           collection(iSweep).ExperimentTimeStamp{length(collection(iSweep).ExperimentTimeStamp)+1} = ExperimentTimeStamp{itest};
       end


       % plot kymograph
       if strcmp(setting.kymographAnalysis.plotKymograph, 'on') | ~strcmp(setting.kymographAnalysis.saveKymograph, 'off') 
           close all
           plotKymograph(opticalContrast(:,:,iSweep), Trajectory, strcat(ExperimentTimeStamp{itest},'_',collection(iSweep).SweepLegend))
       end

       % save kymograph
       if ~strcmp(setting.kymographAnalysis.saveKymograph, 'off') 
           saveas(gcf, strcat(ExperimentFolder,'/kymographs/', strcat(ExperimentTimeStamp{itest},'_',collection(iSweep).SweepLegend)), setting.kymographAnalysis.saveKymograph)
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






  
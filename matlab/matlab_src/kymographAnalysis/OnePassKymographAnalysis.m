function [opticalContrast, Trajectory] = OnePassKymographAnalysis(data, exportFileName, Setting)

%% kymograph preprocessing
opticalContrast = kymographPreprocessing(data, Setting.kymographPreprocessing);

%% trajectory detection

% % create an empty collection 
% Trajectory = struct;
% for j = 1:length(Setting.kymographPreprocessing.Wx)
%     for i = 1:length(Setting.kymographAnalysis.trajectoryProperties)
%         Trajectory(j).(Setting.kymographAnalysis.trajectoryProperties{i}) = [];
%     end
% end

% go through sweeps
for iSweep = 1:size(opticalContrast,3)

    switch Setting.trajectoryDetecton.Title
    
        case 'trackBeforeDetect'
    
            Tracks = trackBeforeDetect(opticalContrast(:,:,iSweep), Setting);
             
            Trajectory0.timeFrame = cell(1, length(Tracks));
            Trajectory0.position = cell(1, length(Tracks));
            Trajectory0.positionRefined = cell(1, length(Tracks));
            trackLength = ones(1, length(Tracks));
            for itrack = 1:length(Tracks)
                Trajectory0.timeFrame{itrack} = Tracks(itrack).timeFrame;
                Trajectory0.position{itrack} = Tracks(itrack).position;
                Trajectory0.positionRefined{itrack} = Tracks(itrack).positionRefined;
                trackLength(itrack) = length(Tracks(itrack).timeFrame);
            end
            %filtering based on Setting.Linking.minTrackLength
            Trajectory0.timeFrame = Trajectory0.timeFrame(trackLength >= Setting.Linking.minTrackLength);
            Trajectory0.position = Trajectory0.position(trackLength >= Setting.Linking.minTrackLength);
            Trajectory0.positionRefined = Trajectory0.positionRefined(trackLength >= Setting.Linking.minTrackLength);

    
        case 'gabClosingTracker'
    
            Tracks = gabClosingTracker( opticalContrast(:,:,iSweep), ...
                peakSign = Setting.Detection.peakSign,...
                pfa = Setting.Detection.pfa, ...
                localOptimumRange = Setting.Detection.localOptimumRange, ...
                boarderRange = Setting.Detection.boarderRange, ...
                positionRefinementMethod = Setting.FeatureExtraction.positionRefinementMethod, ...
                fittingRadius = Setting.FeatureExtraction.fittingRadius, ...
                cut_off_distance = Setting.Linking.cut_off_distance, ...
                unmatched_penalty_distance = Setting.Linking.unmatched_penalty_distance, ...
                flowEstimate = Setting.Linking.flowEstimate_ums * data.Dt/data.Dx, ...
                maxPositiveGab = Setting.Linking.maxPositiveGab, ...
                maxNegativeGab = Setting.Linking.maxNegativeGab, ...
                gab_closing_cut_off_distance = Setting.Linking.gab_closing_cut_off_distance, ...
                gab_closing_penalty_distance = Setting.Linking.gab_closing_penalty_distance, ...
                minTrackLength = Setting.Linking.minTrackLength, ...
                showTrackIds = Setting.Linking.showTrackIds, ...
                exportOptinalFigures = Setting.exportOptinalFigures, ...
                exportFileName = exportFileName, ...
                exportFolderPath = Setting.Path.exportFolder, ...
                exportResolution = Setting.exportDpi, ...
                flipIntensity = Setting.flipIntensity);
            
            if ~isempty(Tracks)
                Trajectory0.timeFrame = Tracks.frames;
                Trajectory0.position = Tracks.positions;
                Trajectory0.positionRefined = Tracks.positions_refined;
            else
                Trajectory0.timeFrame = {};
                Trajectory0.position = {};
                Trajectory0.positionRefined = {};
            end
    
    end

    % trajectory analysis
    TAsetting.Dt = data.Dt; 
    TAsetting.Dx = data.Dx;
    TAsetting.Wx = Setting.kymographPreprocessing.Wx(iSweep);
    
    %TAsetting.channelArea = Setting.channel.area;
    Trajectory0 = trajectoryAnalysis (Trajectory0, Setting.kymographAnalysis.trajectoryProperties, TAsetting, opticalContrast(:,:,iSweep));
    Trajectory0 = rmfield(Trajectory0,'position');
    Trajectory(iSweep) = Trajectory0;

end

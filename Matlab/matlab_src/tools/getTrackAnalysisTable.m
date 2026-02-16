function TrackAnalysisTable = getTrackAnalysisTable(inputFolderPath, fileName)

    % load data
    % load( fullfile(inputFolderPath, 'denoised', [fileName,'.mat']) );
    load( fullfile(inputFolderPath, 'final_tracks', [fileName,'.mat']) );
    load( fullfile(inputFolderPath, 'contrast', [fileName,'.mat']) );

    ProcessingParameters = jsondecode(fileread(...
        fullfile(inputFolderPath, 'processing_parameters', [fileName,'.json']) ));

    % format conversion
    PARTICLES = struct([]);
    
    for iTrack=1:FinalTracks.nTracks
    
        PARTICLES(iTrack).timeFrame = FinalTracks.frames{iTrack};
        PARTICLES(iTrack).position = FinalTracks.positions{iTrack};
        PARTICLES(iTrack).positionRefined = FinalTracks.positions_refined{iTrack};
        % PARTICLES(iTrack).I = FinalTracks.intensities{iTrack};
        PARTICLES(iTrack).I = FinalTracks.contrasts{iTrack};
    end
    
    I2 = C;
    
    % data.Im = R;
    data.Dx = 0.066;
    data.Dt = 0.007;
    
    PT_setting.flowEstimate = ProcessingParameters.Linking.flowEstimate;    
    denoise_setting = struct([]);

    % track analysis table
    TrackAnalysis = evaluateTrajectory(PARTICLES, I2, ...
        {'iOC','D','N','STDiOC','convertUnits'}, ... 
        data, denoise_setting, PT_setting);
    
    TrackAnalysisTable = struct2table(TrackAnalysis, AsArray=true);
    
    % add file name and treck_id
    
    file_name = repelem(convertCharsToStrings(fileName),FinalTracks.nTracks).';
    track_id = (1:FinalTracks.nTracks).';
    
    TrackAnalysisTable = addvars(TrackAnalysisTable, file_name, track_id, 'Before', 'STDiOC');


end
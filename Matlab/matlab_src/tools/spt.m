%% MH, v1.0, 2025_11_12

function spt(rawDataFilePath, Contrast, options)
    
    arguments
        rawDataFilePath
        Contrast

        options.defluctuationMethod = 'mean'
        options.bacgroundEstimationMethod = 'padded_movmean'
        options.Kt = 101
        options.backgroundRemovalMethod = 'subtract'
        options.whiteningMethod = 'std_division'

        options.spaceFilter = 'imgaussfilt'
        options.sigma_x = 1
        options.timeFilter = 'none'
        options.sigma_t = eps
        options.nonLinearFilter = 'none'

        options.pfa = 1e-4
        options.localMinRange = 6

        options.positionRefinementMethod = 'centroid'
        options.fittingRadius = 3

        options.cut_off_distance = 20
        options.unmatched_penalty_distance = 15
        options.flowEstimate = 0, 
        options.maxPositiveGab = 3
        options.maxNegativeGab = 2 
        options.gab_closing_cut_off_distance = 40
        options.gab_closing_penalty_distance =30
        options.minTrackLength = 40

        options.exportImages = false
        options.exportResolution = 300
        options.exportFolderPath = 'export'
        options.visibleFigure = false

    end

    % paths
    [~,fileName,~] = fileparts(rawDataFilePath);
    % [folderPath,fileName,~] = fileparts(rawDataFilePath);
    % [parentFolderPath,folderName,~] = fileparts(folderPath);
    % [~,parentFolderName,~] = fileparts(parentFolderPath);
    
    % load data
    R = imread(rawDataFilePath);
    
    Nt = size(R,1);

    % preprocess
    X = preprocessing(R, ...
            defluctuationMethod=options.defluctuationMethod,...
            bacgroundEstimationMethod=options.bacgroundEstimationMethod,...
            Kt=options.Kt,...
            backgroundRemovalMethod=options.backgroundRemovalMethod,...
            whiteningMethod=options.whiteningMethod);

    % denoising
    Y = denoising(X, ...
        spaceFilter=options.spaceFilter, ...
        sigma_x=options.sigma_x, ...
        timeFilter=options.timeFilter, ...
        sigma_t=options.sigma_t, ...
        nonLinearFilter=options.nonLinearFilter);

    if options.visibleFigure || options.exportImages
        showKymograph(-Y, title='denoised', ...
            exportFigure=options.exportImages, ...
            exportName=fileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'denoised'), ...
            visibleFigure=options.visibleFigure, ...
            exportResolution=options.exportResolution)
    end
 
    % export denoised image as *.mat
    exportMatrix(Y, ...
        exportPath=fullfile(options.exportFolderPath,'denoised',[fileName,'.mat']));
    
    % detection
    Detections = detection(Y, pfa=options.pfa, localMinRange=options.localMinRange);
    
    if options.visibleFigure || options.exportImages
        showKymograph(-Y, Detections=Detections, detectionsIntensitySign='-', title='detections', ...
            exportFigure=options.exportImages, ...
            exportName=fileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'detections'), ...        
            visibleFigure=options.visibleFigure, ...
            exportResolution=options.exportResolution)
    end

    % contrast image
    C = preprocessingDenoising(R, ...
        chainOrder=Contrast.chainOrder, ...
        defluctuationMethod=Contrast.defluctuationMethod, ...
        Kx=Contrast.Kx, ...
        bacgroundEstimationMethod=Contrast.bacgroundEstimationMethod, ...
        Kt=Contrast.Kt, ...
        backgroundRemovalMethod=Contrast.backgroundRemovalMethod, ...
        whiteningMethod=Contrast.whiteningMethod, ...
        spaceFilter=Contrast.spaceFilter, ...
        sigma_x=Contrast.sigma_x, ...
        k_max=Contrast.k_max ...
    );

    % export contrast image as *.mat
    exportMatrix(C, ...
        exportPath=fullfile(options.exportFolderPath,'contrast',[fileName,'.mat']));

    % position refinment
    Detections.position_refined = refinement(Detections.position, Detections.frame, C, ...
        method=options.positionRefinementMethod, ...
        fittingRadius=options.fittingRadius);

    % contrast
    Detections.contrast = C(sub2ind(size(C), Detections.frame, Detections.position));

    Spots = makeSpotTable(Detections);
    
    % export Spots
    exportTable(Spots, ...
        exportPath=fullfile(options.exportFolderPath,'spots',[fileName,'.csv']));
    
    % frame-by-frame linking
    Edges = spotLinking(Spots, Nt, ...
        options.cut_off_distance, options.unmatched_penalty_distance, options.flowEstimate);

    EdgesTable = makeEdgeTable(Edges);

    Tracklets = joinLinkedSpots(EdgesTable, Spots);
    
    if options.visibleFigure || options.exportImages
        showKymograph(-Y, Tracks=Tracklets, detectionsIntensitySign='-', title='tracklets', ...
            exportFigure=options.exportImages, ...
            exportName=fileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'tracklets'), ...        
            visibleFigure=options.visibleFigure, ...
            exportResolution=options.exportResolution);
    end
    
    TrackletsTable = makeTrackletTable(Tracklets);
    
    % gab closing
    [matchedTrackletIds, unmatchedRows] = trackletLinking(TrackletsTable, ...
        options.maxNegativeGab, options.maxPositiveGab, ...
        options.gab_closing_cut_off_distance, options.gab_closing_penalty_distance);
    
    RawTracks = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets);
    
    if options.visibleFigure || options.exportImages
        showKymograph(-Y, Tracks=RawTracks, detectionsIntensitySign='-', title='raw tracks', ...
            exportFigure=options.exportImages, ...
            exportName=fileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'raw_tracks'), ...        
            visibleFigure=options.visibleFigure, ...
            exportResolution=options.exportResolution);
    end
    
    % non-positive gabs
    Tracks = deleteSpotsWithNonPositiveGabs(RawTracks);
    
    % track postprocessing
    FinalTracks = trackPostprocessing(Tracks, options.minTrackLength);
    
    if options.visibleFigure || options.exportImages
        showKymograph(-Y, Tracks=FinalTracks, detectionsIntensitySign='-', title='final tracks', ...
            exportFigure=options.exportImages, ...
            exportName=fileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'final_tracks'), ...        
            visibleFigure=options.visibleFigure, ...
            exportResolution=options.exportResolution);
    end

    % export final tracks as mat-files
    exportMatrix(FinalTracks, ...
        exportPath=fullfile(options.exportFolderPath,'final_tracks',[fileName,'.mat']));
    
    % export processing parameters as a json file
    ProcessingParameters.Preprocessing.defluctuationMethod = options.defluctuationMethod;
    ProcessingParameters.Preprocessing.bacgroundEstimationMethod = options.bacgroundEstimationMethod;
    ProcessingParameters.Preprocessing.Kt = options.Kt;
    ProcessingParameters.Preprocessing.backgroundRemovalMethod = options.backgroundRemovalMethod;
    ProcessingParameters.Preprocessing.whiteningMethod = options.whiteningMethod;

    ProcessingParameters.Denoising.spaceFilter = options.spaceFilter;
    ProcessingParameters.Denoising.sigma_x = options.sigma_x;
    ProcessingParameters.Denoising.timeFilter = options.timeFilter;
    ProcessingParameters.Denoising.sigma_t = options.sigma_t;
    ProcessingParameters.Denoising.nonLinearFilter = options.nonLinearFilter;

    ProcessingParameters.Contrast = Contrast;

    ProcessingParameters.Detection.pfa = options.pfa;
    ProcessingParameters.Detection.localMinRange = options.localMinRange;

    ProcessingParameters.FeatureExtraction.positionRefinementMethod = options.positionRefinementMethod;
    ProcessingParameters.FeatureExtraction.fittingRadius = options.fittingRadius;

    ProcessingParameters.Linking.cut_off_distance = options.cut_off_distance;
    ProcessingParameters.Linking.unmatched_penalty_distance = options.unmatched_penalty_distance;
    ProcessingParameters.Linking.flowEstimate = options.flowEstimate;
    ProcessingParameters.Linking.maxPositiveGab = options.maxPositiveGab;
    ProcessingParameters.Linking.maxNegativeGab = options.maxNegativeGab;
    ProcessingParameters.Linking.gab_closing_cut_off_distance = options.gab_closing_cut_off_distance;
    ProcessingParameters.Linking.gab_closing_penalty_distance = options.gab_closing_penalty_distance;
    ProcessingParameters.Linking.minTrackLength = options.minTrackLength;
    
    exportStructure(ProcessingParameters, ...
        exportPath=fullfile(options.exportFolderPath,'processing_parameters',[fileName,'.json']) );

end
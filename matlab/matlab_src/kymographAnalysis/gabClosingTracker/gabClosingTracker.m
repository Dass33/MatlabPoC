function FinalTracks = gabClosingTracker(C, options)

% MH, v1.4, 2026_02_20

    arguments
        C

        options.flipIntensity = true

        options.peakSign (1,:) {mustBeMember(options.peakSign,['negative','positive', 'negative-positive'])} = 'negative'
        options.pfa = 1e-4
        options.localOptimumRange = 6
        options.boarderRange = 6

        options.positionRefinementMethod = 'centroid'
        options.fittingRadius = 3

        options.cut_off_distance = 20
        options.unmatched_penalty_distance = 15
        options.flowEstimate = 0, 
        options.maxPositiveGab = 3
        options.maxNegativeGab = 2 
        options.gab_closing_cut_off_distance = 40
        options.gab_closing_penalty_distance = 30
        options.minTrackLength = 5

        options.exportOptinalFigures = false
        options.exportFileName = '01'
        options.exportFolderPath = 'export'
        options.exportResolution = 300
        options.showTrackIds = true

    end      

    % export contrast image 
    if options.exportOptinalFigures
        showKymograph(C, title='contrast', ...
            exportFigure=options.exportOptinalFigures, ...
            exportName=options.exportFileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'contrast'), ...
            visibleFigure=false, ...
            exportResolution=options.exportResolution,...
            flipIntensity=options.flipIntensity)
    end

    % export contrast image as *.mat
    if options.exportOptinalFigures
        exportMatrix(C, ...
            exportPath=fullfile(options.exportFolderPath,'contrast',[options.exportFileName,'.mat']));
    end

    % detection
    Detections = detection(C, ...
        peakSign=options.peakSign, ...        
        pfa=options.pfa, ...
        localOptimumRange=options.localOptimumRange, ...
        boarderRange=options.boarderRange);

    % export contrast image with detections
    if options.exportOptinalFigures
        showKymograph(C, ...
            title='detections', ...
            Detections=Detections, ...            
            exportFigure=options.exportOptinalFigures, ...
            exportName=options.exportFileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'detections'), ...        
            visibleFigure=false, ...
            exportResolution=options.exportResolution, ...
            flipIntensity=options.flipIntensity)
    end

    % position refinement
    Detections.position_refined = position_refinement(...
        Detections.position, ...
        Detections.frame, ...
        C, ...
        method=options.positionRefinementMethod, ...
        fittingRadius=options.fittingRadius);

    % contrast values
    Detections.contrast = C(sub2ind(size(C), Detections.frame, Detections.position));

    % convert to table
    Spots = makeSpotTable(Detections);
    
    % export Spots
    if options.exportOptinalFigures
        exportTable(Spots, ...
            exportPath=fullfile(options.exportFolderPath,'detections',[options.exportFileName,'.csv']));
    end

    % frame-by-frame linking
    Nt = size(C,1);

    Edges = spotLinking(Spots, Nt, ...
        options.cut_off_distance, ...
        options.unmatched_penalty_distance, ...
        options.flowEstimate);

    EdgesTable = makeEdgeTable(Edges);

    % jump distance statistics
    if ~isempty(EdgesTable.jump_distance)
        std_jump_distance = std(EdgesTable.jump_distance);
    end

    Tracklets = joinLinkedSpots(EdgesTable, Spots);
    
    TrackletsTable = makeTrackletTable(Tracklets);
    
    % gab closing
    [matchedTrackletIds, unmatchedRows] = trackletLinking(TrackletsTable, ...
        options.maxNegativeGab, ...
        options.maxPositiveGab, ...
        options.gab_closing_cut_off_distance, ...
        options.gab_closing_penalty_distance, ...
        options.flowEstimate);
    
    RawTracks = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets);
    
    % delte spots with non-positive gabs
    PositiveGapTracks = deleteNegativeGapSpots(RawTracks);      

    % filter short tracks
    FilteredTracks = trackFiltering(PositiveGapTracks, options.minTrackLength);

    % gap filling

    if exist('std_jump_distance', 'var')
        % gap_local_optimum_range = round(std_jump_distance);
        gap_local_optimum_range = 2*round(std_jump_distance);
    else
        gap_local_optimum_range = 1;
    end

    GapFilledTracks = gapFilling(FilteredTracks, C, C, ...
        gap_local_optimum_range=gap_local_optimum_range, ...
        peakSign=options.peakSign, ...        
        positionRefinementMethod=options.positionRefinementMethod, ...
        fittingRadius=options.fittingRadius);

    % transpose cell structure arrays
    FinalTracks = GapFilledTracks;
    % if ~isempty(GapFilledTracks)
    %     FinalTracks = structfun(@transpose, GapFilledTracks, 'UniformOutput', false);
    % else
    %     FinalTracks = GapFilledTracks;
    % end

    % export contrast image with final tracks
    if options.exportOptinalFigures
        showKymograph(C, ...
            title='final tracks', ...
            Tracks=FinalTracks, ...
            exportFigure=options.exportOptinalFigures, ...
            exportName=options.exportFileName, ...
            exportDirectory=fullfile(options.exportFolderPath,'final_tracks'), ...        
            visibleFigure=false, ...
            exportResolution=options.exportResolution, ...
            flipIntensity=options.flipIntensity)
    end

    % export final tracks
    if options.exportOptinalFigures
        exportMatrix(FinalTracks, ...
            exportPath=fullfile(options.exportFolderPath,'final_tracks',[options.exportFileName,'.mat']));
    end

end
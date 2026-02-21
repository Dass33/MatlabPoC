function Tracklets = joinLinkedSpots(EdgesTable, Spots)

    % init
    clear Tracklets
    Tracklets.spot_ids = {};
    nTracks = 0;
    
    % loop over all edges
    for iEdge = 1:size(EdgesTable,1)
    
        sourceSpot = EdgesTable(iEdge,:).source_spot_id;
        targetSpot = EdgesTable(iEdge,:).target_spot_id;
    
        % is the source spot an end of some tracklets?
        isSourceSpotTrackletEnd = false;
    
        for iTracklet = 1:length(Tracklets.spot_ids)
    
            if Tracklets.spot_ids{iTracklet}(end) == sourceSpot
                isSourceSpotTrackletEnd = true;
                break
            end
    
        end
    
        % if yes, then extend existing tracklet that has id of iTracklet due to
        % the breaked loop
        if isSourceSpotTrackletEnd
    
            Tracklets.spot_ids{iTracklet} = [Tracklets.spot_ids{iTracklet}; targetSpot];
    
            % otherwise, create new tracklet
        else
    
            nTracks = nTracks + 1;
            Tracklets.spot_ids{nTracks} = [sourceSpot; targetSpot];
    
        end
    
    end

    % keep spot frames, positions and intensities in Tracklet structure
    Tracklets.frames = cellfun(@(x) Spots.frame(x), Tracklets.spot_ids, UniformOutput=false);
    Tracklets.positions = cellfun(@(x) Spots.position(x), Tracklets.spot_ids, UniformOutput=false);
    Tracklets.positions_refined = cellfun(@(x) Spots.position_refined(x), Tracklets.spot_ids, UniformOutput=false);
    Tracklets.intensities = cellfun(@(x) Spots.intensity(x), Tracklets.spot_ids, UniformOutput=false);
    Tracklets.contrasts = cellfun(@(x) Spots.contrast(x), Tracklets.spot_ids, UniformOutput=false);

end
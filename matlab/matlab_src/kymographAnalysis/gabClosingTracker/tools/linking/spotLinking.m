function Edges = spotLinking(Spots, nFrames, cut_off_distance, unmatched_penalty_distance, flowEstimate)

    % init
    Edges.source_frame = [];
    Edges.source_spot_id = [];
    Edges.target_spot_id = [];
    Edges.jump_distance = [];
        
    for iFrame = 1:(nFrames-1)
    
        source_frame = iFrame;
        target_frame = iFrame+1;
    
        % source_positions = Spots.position(Spots.frame==source_frame);
        % target_positions = Spots.position(Spots.frame==target_frame);
        source_positions = Spots.position_refined(Spots.frame==source_frame);
        target_positions = Spots.position_refined(Spots.frame==target_frame);
        
        % two-set pairwise squared Euclidean distance matrix as a cost matrix
        linking_cost = squaredPairDistance( source_positions, target_positions - flowEstimate);
    
        % set cut-off distances to infinity
        linking_cost(linking_cost > cut_off_distance^2) = inf;
    
        % [Duff-Koster_2001]
        matchIndexes = matchpairs(linking_cost, unmatched_penalty_distance^2);
    
        source_positions_linked = source_positions(matchIndexes(:,1));
        target_positions_linked = target_positions(matchIndexes(:,2));
    
        source_ids_linked = extractElements( Spots.spot_id(Spots.frame==source_frame), matchIndexes(:,1) );
        taget_ids_linked = extractElements( Spots.spot_id(Spots.frame==target_frame), matchIndexes(:,2) );
    
        % store all edge properties into one structure
        Edges.source_spot_id = [Edges.source_spot_id; source_ids_linked];
        Edges.target_spot_id = [Edges.target_spot_id; taget_ids_linked];
    
        % source frame
        nMatches = size(matchIndexes,1);
        Edges.source_frame = [Edges.source_frame; iFrame * ones(nMatches, 1)];
    
        Edges.jump_distance = [Edges.jump_distance; target_positions_linked-source_positions_linked];
    
    end

    % Edges.nEdges = length(Edges.source_spot_id);

end
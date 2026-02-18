function [matchedTrackletIds, unmatchedRows] = trackletLinking(TT, maxNegativeGab, maxPositiveGab, ...
    gab_closing_cut_off_distance, gab_closing_penalty_distance)

    % allowable gab closing tracklets
    frameDiff = -TT.end_frame + TT.start_frame .';
    gabClosableMask = frameDiff >= (1-maxNegativeGab) & frameDiff <=(maxPositiveGab+1);
    
    % source_end_positions = TT.end_position;
    % destination_start_positions = TT.start_position;    
    source_end_positions = TT.end_position_refined;
    destination_start_positions = TT.start_position_refined;    
    
    gabClosingCost = squaredPairDistance( source_end_positions, destination_start_positions);
    
    gabClosingCost(~gabClosableMask) = inf;
    gabClosingCost(gabClosingCost > gab_closing_cut_off_distance^2) = inf;
    gabClosingCost( eye( size(TT,1), 'logical') ) = inf;
    
    [matchedTrackletIds, unmatchedRows, ~] = matchpairs(gabClosingCost, gab_closing_penalty_distance^2);
    matchedTrackletIds = sortByFirstColumn(matchedTrackletIds);

end
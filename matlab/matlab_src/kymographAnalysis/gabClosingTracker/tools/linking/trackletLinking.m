% MH, v1.0, 2025_12_13

function [matchedTrackletIds, unmatchedRows] = trackletLinking(...
    TrackletsTable, ...
    maxNegativeGap, ...
    maxPositiveGap, ...
    gap_closing_cut_off_distance, ...
    gap_closing_penalty_distance, ...
    flowEstimate)

    % allowable gap closing tracklets
    frameDiff = -TrackletsTable.end_frame + TrackletsTable.start_frame .';
    gapClosableMask = frameDiff >= (1-maxNegativeGap) & frameDiff <=(maxPositiveGap+1);
    
    % coarse postitions
    % source_end_positions = TrackletsTable.end_position;
    % destination_start_positions = TrackletsTable.start_position;    

    % fine postitions
    % source_end_positions = TrackletsTable.end_position_refined;
    % destination_start_positions = TrackletsTable.start_position_refined;    

    % fine postitions with flow correction
    source_end_positions = TrackletsTable.end_position_refined - flowEstimate * TrackletsTable.end_frame;
    destination_start_positions = TrackletsTable.start_position_refined - flowEstimate * TrackletsTable.start_frame;    
        
    gapClosingCost = squaredPairDistance( source_end_positions, destination_start_positions);
    
    gapClosingCost(~gapClosableMask) = inf;
    gapClosingCost(gapClosingCost > gap_closing_cut_off_distance^2) = inf;
    gapClosingCost( eye( size(TrackletsTable,1), 'logical') ) = inf;
    
    [matchedTrackletIds, unmatchedRows, ~] = matchpairs(gapClosingCost, gap_closing_penalty_distance^2);
    matchedTrackletIds = sortByFirstColumn(matchedTrackletIds);

end
function Tracks = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets)

% MH, v1.1, 2026_01_13
    
    clear Tracks

    Tracks.tracklet_ids = {};   
    Tracks.spot_ids = {};
    Tracks.frames = {};
    Tracks.positions = {}; 
    Tracks.positions_refined = {};
    Tracks.intensities = {}; 
    Tracks.contrasts = {}; 

    nTracks = 0;

    for iMatchedPair = 1:size(matchedTrackletIds,1)
    
        sourceTracklet = matchedTrackletIds(iMatchedPair,1);
        destinationTracklet = matchedTrackletIds(iMatchedPair,2);
    
        % is the source tracklet an end of some track?
        isSourceTrackletTrackEnd = false;
    
        for iTrack = 1:length(Tracks.tracklet_ids)
    
            if Tracks.tracklet_ids{iTrack}(end) == sourceTracklet
                isSourceTrackletTrackEnd = true;
                break
            end
    
        end
    
        % if yes, then extend existing track
        if isSourceTrackletTrackEnd
    
            Tracks.tracklet_ids{iTrack} = [  Tracks.tracklet_ids{iTrack}; destinationTracklet];
    
        % otherwise, create new track
        else
    
            nTracks = nTracks + 1;
            Tracks.tracklet_ids{nTracks} = [sourceTracklet; destinationTracklet];
    
        end
    
    end
    
    % add single-tracklet tracks
    linkedTrackletsEnd = cellfun(@(X) X(end), Tracks.tracklet_ids).';
    singleTrackletTracks = setdiff(unmatchedRows,linkedTrackletsEnd);
    
    % concatenate multi-tracklet tracks with single-tracklet tracks
    Tracks.tracklet_ids = horzcat(Tracks.tracklet_ids, num2cell(singleTrackletTracks.'));
    nTracks = nTracks + length(singleTrackletTracks);
    
    % check total number of tracklets
    if ~sum(cellfun(@length, Tracks.tracklet_ids)) == nTracks
        disp('total number of tracklets is incorrect')
    end

    % merging linked tracklets into single track
    
    for i = 1:length(Tracks.tracklet_ids)
    
        Tracks.spot_ids{i} = vertcat(Tracklets.spot_ids{ Tracks.tracklet_ids{i} });
        Tracks.frames{i} = vertcat(Tracklets.frames{ Tracks.tracklet_ids{i} });
        Tracks.positions{i} = vertcat(Tracklets.positions{ Tracks.tracklet_ids{i} });
        Tracks.positions_refined{i} = vertcat(Tracklets.positions_refined{ Tracks.tracklet_ids{i} });
        Tracks.intensities{i} = vertcat(Tracklets.intensities{ Tracks.tracklet_ids{i} });
        Tracks.contrasts{i} = vertcat(Tracklets.contrasts{ Tracks.tracklet_ids{i} });  

    end


end
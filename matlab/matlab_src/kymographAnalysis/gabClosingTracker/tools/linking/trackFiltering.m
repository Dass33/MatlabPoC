function FinalTracks = trackFiltering(Tracks, minTrackLength)

% MH, v1.1, 2026_01_13

    if ~isempty(Tracks)

        track_length = cellfun(@(x) x(end) - x(1), Tracks.frames);        

        longerTracksIndexes = track_length > minTrackLength;
        
        if any(track_length > minTrackLength)

            FinalTracks.tracklet_ids = {Tracks.tracklet_ids{ longerTracksIndexes }};
            FinalTracks.spot_ids = {Tracks.spot_ids{ longerTracksIndexes }};
            FinalTracks.frames = {Tracks.frames{ longerTracksIndexes }};
            FinalTracks.positions = {Tracks.positions{ longerTracksIndexes }};
            FinalTracks.positions_refined = {Tracks.positions_refined{ longerTracksIndexes }};
            FinalTracks.intensities = {Tracks.intensities{ longerTracksIndexes }};
            FinalTracks.contrasts = {Tracks.contrasts{ longerTracksIndexes }};
            FinalTracks.length = num2cell(track_length(longerTracksIndexes));
                
        else
    
            FinalTracks = struct([]);
    
        end

    else

        FinalTracks = Tracks;
    
    end

end
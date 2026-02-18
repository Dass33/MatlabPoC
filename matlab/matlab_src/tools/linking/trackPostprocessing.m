function FinalTracks = trackPostprocessing(Tracks, minTrackLength)

    if Tracks.nTracks > 0

        Tracks.length = cellfun(@length, Tracks.frames);
        
        longerTracksIndexes = Tracks.length > minTrackLength;
        
        FinalTracks.tracklet_ids = {Tracks.tracklet_ids{ longerTracksIndexes }};
        FinalTracks.spot_ids = {Tracks.spot_ids{ longerTracksIndexes }};
        FinalTracks.frames = {Tracks.frames{ longerTracksIndexes }};
        FinalTracks.positions = {Tracks.positions{ longerTracksIndexes }};
        FinalTracks.positions_refined = {Tracks.positions_refined{ longerTracksIndexes }};
        FinalTracks.intensities = {Tracks.intensities{ longerTracksIndexes }};
        FinalTracks.contrasts = {Tracks.contrasts{ longerTracksIndexes }};
        FinalTracks.length = Tracks.length(longerTracksIndexes);
        
        FinalTracks.nTracks = sum(longerTracksIndexes);

    else

        FinalTracks = Tracks;

    end
    
end
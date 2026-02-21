function Tracks = deleteNegativeGapSpots(Tracks)

    for iTrack = 1:length(Tracks.intensities)
    
        if any( diff( Tracks.frames{iTrack} ) < 1)
    
            nSpots = length( Tracks.frames{iTrack} );
    
            iSpot = 1;
    
            while iSpot < nSpots
    
                delta_frame = Tracks.frames{iTrack}(iSpot+1) - Tracks.frames{iTrack}(iSpot);
    
                while delta_frame < 1
    
                    if Tracks.intensities{iTrack}(iSpot) <= Tracks.intensities{iTrack}(iSpot+1)
                        
                        % delete spot (iSpot+1)
                        Tracks.spot_ids{iTrack}(iSpot+1) = [];
                        Tracks.frames{iTrack}(iSpot+1) = [];
                        Tracks.positions{iTrack}(iSpot+1) = [];
                        Tracks.positions_refined{iTrack}(iSpot+1) = [];
                        Tracks.intensities{iTrack}(iSpot+1) = [];
                        Tracks.contrasts{iTrack}(iSpot+1) = [];
    
                        nSpots = nSpots - 1;
    
                    else
    
                        % delete spot iSpot
                        Tracks.spot_ids{iTrack}(iSpot) = [];
                        Tracks.frames{iTrack}(iSpot) = [];
                        Tracks.positions{iTrack}(iSpot) = [];
                        Tracks.positions_refined{iTrack}(iSpot) = [];
                        Tracks.intensities{iTrack}(iSpot) = [];
                        Tracks.contrasts{iTrack}(iSpot) = [];
    
                        nSpots = nSpots - 1;

                        if iSpot > 1
                            iSpot = iSpot - 1;
                        end
                        
                    end
    
                    if (iSpot+1) > nSpots
                        break
                    end

                    delta_frame = Tracks.frames{iTrack}(iSpot+1) - Tracks.frames{iTrack}(iSpot);
    
                end
    
                iSpot = iSpot +1;
    
            end
    
        end
    
    end


end
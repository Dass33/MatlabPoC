function GapFilledTracks = gapFilling(FilteredTracks, Y, C, options)
% MH, v1.1, 2026_01_09

    arguments
        FilteredTracks
        Y
        C
        options.gap_local_optimum_range
        options.peakSign
        options.positionRefinementMethod = 'centroid'
        options.fittingRadius = 3
    end

    Nx = size(Y,2);

    % if FilteredTracks.nTracks > 0

    if ~isempty(FilteredTracks)

        for iTrack = 1 : length(FilteredTracks.frames)
        
            gap_starts = find(diff(FilteredTracks.frames{iTrack})>1);
            
            if ~isempty(gap_starts)
                
                % create empty cell arrays
                gap_filling_frames = cell(1,length(gap_starts));
                gap_filling_positions = cell(1,length(gap_starts));
        
                for iGap = 1 : length(gap_starts)
                
                    gap_start_frame = FilteredTracks.frames{iTrack}(gap_starts(iGap));
                    gap_end_frame = FilteredTracks.frames{iTrack}(gap_starts(iGap)+1);
                    
                    gap_filling_frames{iGap} = (gap_start_frame+1):(gap_end_frame-1);
                    
                    gap_length = length(gap_filling_frames{iGap});
                    
                    gap_start_position = FilteredTracks.positions{iTrack}(gap_starts(iGap));
                    gap_end_position = FilteredTracks.positions{iTrack}(gap_starts(iGap)+1);
                    
                    gap_filling_positions_line = round(linspace(gap_start_position, gap_end_position, gap_length+2));
                    gap_filling_positions_line = gap_filling_positions_line(2:end-1);            
                    
                    gap_filling_positions{iGap} = zeros(1,gap_length);
                    
                    for iSpot = 1 : gap_length           
                        
                        position_range_indexes = max(gap_filling_positions_line(iSpot)-options.gap_local_optimum_range,1) : ...
                            min(gap_filling_positions_line(iSpot)+options.gap_local_optimum_range,Nx);
                        
                        intensity_range = Y( gap_filling_frames{iGap}(iSpot), position_range_indexes );
                        
                        switch options.peakSign 
                            case 'negative'
                                [~, arg_optimum] = min(intensity_range);
                            case 'positive'
                                [~, arg_optimum] = max(intensity_range);
                            case 'negative-positive'
                                arg_optimum = round(length(position_range_indexes)/2);
                        end

                        gap_filling_positions{iGap}(iSpot) = position_range_indexes(arg_optimum);
                    
                    end
                
                end
        
                % insert filling
                GapFilledTracks.frames{iTrack} = FilteredTracks.frames{iTrack}(1:gap_starts(1));
                GapFilledTracks.positions{iTrack} = FilteredTracks.positions{iTrack}(1:gap_starts(1));
            
                for iGap = 1 : length(gap_starts)-1
                    GapFilledTracks.frames{iTrack} = [GapFilledTracks.frames{iTrack}; gap_filling_frames{iGap}.'];
                    GapFilledTracks.positions{iTrack} = [GapFilledTracks.positions{iTrack}; gap_filling_positions{iGap}.'];
        
                    GapFilledTracks.frames{iTrack} =  [GapFilledTracks.frames{iTrack}; ...
                        FilteredTracks.frames{iTrack}(gap_starts(iGap)+1:gap_starts(iGap+1))];
        
                    GapFilledTracks.positions{iTrack} =  [GapFilledTracks.positions{iTrack}; ...
                        FilteredTracks.positions{iTrack}(gap_starts(iGap)+1:gap_starts(iGap+1))];
                end
                
                GapFilledTracks.frames{iTrack} = [GapFilledTracks.frames{iTrack}; gap_filling_frames{end}.'];
                GapFilledTracks.positions{iTrack} = [GapFilledTracks.positions{iTrack}; gap_filling_positions{end}.'];
        
                GapFilledTracks.frames{iTrack} =  [GapFilledTracks.frames{iTrack}; ...
                    FilteredTracks.frames{iTrack}(gap_starts(end)+1:end)];
        
                GapFilledTracks.positions{iTrack} = [GapFilledTracks.positions{iTrack}; ...
                    FilteredTracks.positions{iTrack}(gap_starts(end)+1:end)];        
        
            else
        
                GapFilledTracks.frames{iTrack} = FilteredTracks.frames{iTrack};
                GapFilledTracks.positions{iTrack} = FilteredTracks.positions{iTrack};
                
            end
        
        end 
        
        % add missing properties
        GapFilledTracks.length = cellfun(@length, GapFilledTracks.frames);
        
        for iTrack = 1 : length(GapFilledTracks.frames)
        
            GapFilledTracks.positions_refined{iTrack} = position_refinement(...
                GapFilledTracks.positions{iTrack}, GapFilledTracks.frames{iTrack}, C, ...
                method=options.positionRefinementMethod, fittingRadius=options.fittingRadius);
        
            GapFilledTracks.intensities{iTrack} = Y( ...
                sub2ind(size(Y), GapFilledTracks.frames{iTrack}, GapFilledTracks.positions{iTrack}));
        
            GapFilledTracks.contrasts{iTrack} = C( ...
                sub2ind(size(C), GapFilledTracks.frames{iTrack}, GapFilledTracks.positions{iTrack}));
        
        end

    else

        GapFilledTracks = FilteredTracks;

    end

end
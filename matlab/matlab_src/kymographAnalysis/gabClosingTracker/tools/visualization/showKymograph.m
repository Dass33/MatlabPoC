function showKymograph(I, options)

% MH, v2.3, 2026_01_22

    arguments

        I

        options.title = ''
        options.xlabel = 'x [px]'
        options.ylabel = 't [frames]'
        options.zlabel = 'intensity'        
        options.cmap = "parula"
        options.figPosition = [750, 200, 430, 850]
        options.alpha = 1
        options.view = 'xy'
        options.clim = "auto"
        options.xlim = "auto"
        options.ylim = "auto"
        options.zlim = "auto"
        options.titleInterpreter = 'none'
        options.fontsize = "default"
        options.showColorbar = true
        options.flipIntensity = true
        
        options.showText = false
        options.text = ''        
        options.text_x = 0
        options.text_y = 0
        options.textFontSize = 10
        options.textColor = 'k'

        options.showRectangle = false
        options.rectangePosition = [0,0,1,1]
        options.rectangleEdgeColor = 'k'
        options.rectangleLineWidth = 0.5

        options.Detections = struct([])

        options.showDetectionIds = false
        options.detectionIdPositionOffset = 5
        options.detectionIdFrameOffset = 25
        options.detectionIdIntensityRelativeOffset = 1.1
        options.detectionsMarkerSize = 5
        options.detectionRefined = false
        options.detectionsLineWidth = 0.5

        options.Tracks = struct([])

        options.showTrackIds = false
        options.trackIdColor ='k'
        options.trackIdPositionOffset = 5
        options.trackIdFrameOffset = 25
        options.trackIdIntensityRelativeOffset = 1.1
        options.trackIdIntensityOffset = 0
        options.trackRandomizedColoring = true
        options.trackColormap = 'jet'

        options.exportFigure = false
        options.exportMatlabFig = false
        options.exportName = '01'
        options.exportDirectory = '.'
        options.exportResolution = 300
        options.visibleFigure = true

    end

    if options.visibleFigure
        fig=figure;
    else
        fig=figure('visible','off');
    end

    if options.flipIntensity
        surf(-I, EdgeColor='none', FaceAlpha=options.alpha)        
    else
        surf(I, EdgeColor='none', FaceAlpha=options.alpha)        
    end

    hold on

    if ischar(options.view)
        switch options.view
            case 'xy'
                view(0,90)
            case 'xz'
                view(0,0) 
            case 'yz'        
                view(90,0) 
            case 'xyz'
                view(3)
        end 
    else
        view(options.view)
    end

    if options.flipIntensity
        options.zlabel = ['-',options.zlabel];
    end

    title(options.title, 'Interpreter', options.titleInterpreter)
    xlabel(options.xlabel)
    ylabel(options.ylabel)
    zlabel(options.zlabel)

    if isnumeric(options.fontsize)
        fontsize(options.fontsize,"points")
    else
        fontsize(options.fontsize)
    end

    if options.showColorbar
        colorbar
    end

    axis tight
    clim(options.clim)
    xlim(options.xlim)
    ylim(options.ylim)
    zlim(options.zlim)
    colormap(options.cmap)

    if options.showText
        text(options.text_x,options.text_y,options.text, ...
            FontSize=options.textFontSize,...
            Color=options.textColor)
    end

    if options.showRectangle
        rectangle(...
            Position=options.rectangePosition,...
            EdgeColor=options.rectangleEdgeColor,...
            LineWidth=options.rectangleLineWidth);
    end

    if ~isempty(options.Detections)

        if ~isempty(options.Detections.intensity)
    
            if options.flipIntensity
                detectionsIntensity = -options.Detections.intensity;    
            else
                detectionsIntensity = options.Detections.intensity;
            end
                    
            if options.detectionRefined

                scatter3(...
                    options.Detections.position_refined,...
                    options.Detections.frame,...
                    detectionsIntensity,...
                    options.detectionsMarkerSize, 'k', 'filled', ...
                    MarkerEdgeColor='w',LineWidth=options.detectionsLineWidth);    

                % detection ids
                if options.showDetectionIds
                    for iDetection = 1 : length(options.Detections.frame)
    
                        text(...
                            options.Detections.position_refined(iDetection) + options.detectionIdPositionOffset,...
                            options.Detections.frame(iDetection) + options.detectionIdFrameOffset,...
                            detectionsIntensity(iDetection) * options.detectionIdIntensityRelativeOffset,...
                            num2str(iDetection),...
                            FontSize=options.textFontSize,...
                            Color='k')
                        
                    end
                end

            else

                scatter3(...
                    options.Detections.position,...
                    options.Detections.frame,...
                    detectionsIntensity,...
                    options.detectionsMarkerSize, 'k', 'filled', ...
                    MarkerEdgeColor='w',LineWidth=options.detectionsLineWidth);     

                % detection ids
                if options.showDetectionIds
                    for iDetection = 1 : length(options.Detections.frame)
    
                        text(...
                            options.Detections.position(iDetection) + options.detectionIdPositionOffset,...
                            options.Detections.frame(iDetection) + options.detectionIdFrameOffset,...
                            detectionsIntensity(iDetection) * options.detectionIdIntensityRelativeOffset,...
                            num2str(iDetection),...
                            FontSize=options.textFontSize,...
                            Color='k')
                        
                    end
                end

            end

        end

    end

    if ~isempty(options.Tracks) 
                
        if ~isempty(options.Tracks.intensities) 

            if options.flipIntensity
                trackIntensities = cellfun(@(x) -x, options.Tracks.intensities, 'UniformOutput', false);                        
            else
                trackIntensities = options.Tracks.intensities;
            end
            
            nTracks = length(options.Tracks.intensities);

            switch options.trackColormap
                case 'jet'
                    trackColors = jet(nTracks);
                case 'lines'
                    trackColors = lines(nTracks);                    
                case 'parula'
                    trackColors = parula(nTracks);       
                case 'white'
                    trackColors = ones(nTracks,3);                    
                case 'hsv'
                    trackColors = hsv(nTracks);                          
                otherwise
                    trackColors = lines(nTracks);
            end

            if options.trackRandomizedColoring
                trackColors = trackColors(randperm(nTracks),:);
            end

            for iTracklet = 1:nTracks
                
                if ~isempty(options.Tracks.frames{iTracklet})

                    % track
                    plot3( ...
                        options.Tracks.positions_refined{iTracklet}, ...
                        options.Tracks.frames{iTracklet}, ...
                        trackIntensities{iTracklet}, ...
                        Color=trackColors(iTracklet,:))
                
                    % head = first spot
                    scatter3(...
                        options.Tracks.positions_refined{iTracklet}(1),...
                        options.Tracks.frames{iTracklet}(1),...
                        trackIntensities{iTracklet}(1),...
                        options.detectionsMarkerSize, 'k', 'filled', MarkerEdgeColor='w',LineWidth=options.detectionsLineWidth);  
    
                    % tail = last spot
                    scatter3(...
                        options.Tracks.positions_refined{iTracklet}(end),...
                        options.Tracks.frames{iTracklet}(end),...
                        trackIntensities{iTracklet}(end),...
                        options.detectionsMarkerSize, 'k', 'filled', MarkerEdgeColor='w',LineWidth=options.detectionsLineWidth);  
                    
                    % track ids
                    if options.showTrackIds
                        text(...
                            options.Tracks.positions_refined{iTracklet}(1) + options.trackIdPositionOffset,...
                            options.Tracks.frames{iTracklet}(1) + options.trackIdFrameOffset,...
                            trackIntensities{iTracklet}(1) * options.trackIdIntensityRelativeOffset + ...
                            options.trackIdIntensityOffset, num2str(iTracklet),...
                        FontSize=options.textFontSize,...
                        Color=options.trackIdColor,...
                        BackgroundColor=trackColors(iTracklet,:))
                    end

                end

            end

        end

    end

    if options.exportFigure

        if ~exist(options.exportDirectory, 'dir')
            mkdir(options.exportDirectory);
        end

        exportgraphics(fig,fullfile(options.exportDirectory,[options.exportName,'.png']),...
            'Resolution',options.exportResolution);

        if options.exportMatlabFig
            saveas(fig,fullfile(options.exportDirectory,[options.exportName,'.fig']));
        end
        
    end

    if ~options.visibleFigure
        close
    end
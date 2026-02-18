% mh, v1.3, 2025_09_11

function showKymograph(I, options)

    arguments

        I

        options.method = "surf"
        options.title = ''
        options.xlabel = 'x [px]'
        options.ylabel = 't [frames]'
        options.zlabel = 'intensity'        
        options.cmap = "parula"
        options.figPosition = [750, 200, 430, 850]
        options.showColorbar = true
        options.alpha = 1
        options.view = 'xy'
        options.clim = "auto"
        options.titleInterpreter = 'none'
        
        options.Detections = struct([])
        options.detectionsMarkerSize = 5
        options.detectionsIntensitySign = 'abs'
        options.detectionRefined = false

        options.Tracks = struct([])

        options.exportFigure=false
        options.exportName='01'
        options.exportDirectory='.'
        options.exportResolution = 300
        options.visibleFigure = true

    end

    if options.visibleFigure
        fig=figure;
    else
        fig=figure('visible','off');
    end

    switch options.method

        case "imshow"

            imshow(I, []); 
            fig.Position=options.figPosition;        

        case "imagesc"

            imagesc(I);
            fig.Position=options.figPosition;        

        case "surf"

            surf(I, EdgeColor='none', FaceAlpha=options.alpha)        

            
            if ~isempty(options.Detections)

                hold on

                switch options.detectionsIntensitySign                    
                    case 'abs'
                        detectionsIntensity = abs(options.Detections.intensity);
                    case '+'
                        detectionsIntensity = options.Detections.intensity;
                    case '-'
                        detectionsIntensity = -options.Detections.intensity;    
                end
                        
                if options.detectionRefined
                    scatter3(...
                        options.Detections.position_refined,...
                        options.Detections.frame,...
                        detectionsIntensity,...
                        options.detectionsMarkerSize, 'k', 'filled', MarkerEdgeColor='w');                    
                else
                    scatter3(...
                        options.Detections.position,...
                        options.Detections.frame,...
                        detectionsIntensity,...
                        options.detectionsMarkerSize, 'k', 'filled', MarkerEdgeColor='w');
                end

            end

            if ~isempty(options.Tracks) 
                if options.Tracks.nTracks > 0
    
                    switch options.detectionsIntensitySign                    
                        case 'abs'
                            trackIntensities = cellfun(@abs, options.Tracks.intensities, 'UniformOutput', false);
                        case '+'
                            trackIntensities = options.Tracks.intensities;
                        case '-'
                            trackIntensities = cellfun(@(x) -x, options.Tracks.intensities, 'UniformOutput', false);                        
                    end
    
                    hold on
                    
                    nTracks = length(options.Tracks.intensities);
    
                    trackColors = jet(nTracks);
                    trackColors = trackColors(randperm(nTracks),:);
                                    
                    for iTracklet = 1:nTracks
                    
                        plot3( ...
                            options.Tracks.positions_refined{iTracklet}, ...
                            options.Tracks.frames{iTracklet}, ...
                            trackIntensities{iTracklet}, ...
                            Color=trackColors(iTracklet,:))
                    
                    end
    
                end

            end

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

            switch options.detectionsIntensitySign
                case 'abs'
                    options.zlabel = ['|',options.zlabel,'|'];
                case '-'
                    options.zlabel = ['-',options.zlabel];
            end

            zlabel(options.zlabel)

    end  

    if options.showColorbar
        colorbar
    end

    title(options.title, 'Interpreter', options.titleInterpreter)
    xlabel(options.xlabel)
    ylabel(options.ylabel)
    axis tight
    clim(options.clim);
    colormap(options.cmap)

    if options.exportFigure

        if ~exist(options.exportDirectory, 'dir')
            mkdir(options.exportDirectory);
        end

        exportPath = fullfile(options.exportDirectory,[options.exportName,'.png']);

        exportgraphics(fig,exportPath,'Resolution',options.exportResolution);

    end
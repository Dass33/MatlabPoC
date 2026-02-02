function fillTwoPlots(x,low,up,options)

    arguments
        
        x 
        low 
        up
        
        options.color = [0, 0.4470, 0.7410]
        options.alpha = 0.5
        options.DisplayName = 'fill'
        
    end

    fill([x, fliplr(x)], [low, fliplr(up)], ...
        options.color, ...
        FaceAlpha=options.alpha, ...
        EdgeColor='none', ...
        DisplayName=options.DisplayName)

end
function positionsRefined = refinement(positions, frames, Y, options)

    arguments
        positions
        frames
        Y
        options.method = 'centroid'
        options.fittingRadius = 3
        options.fitType = 'gauss1'
    
    end
    
    positionsRefined = positions;
    
    nDetections = length(positions);
    Nx = size(Y,2);
    
    switch options.method
    
        case 'parabolic'
    
            for iDetection = 1:nDetections
    
                t_molecule = frames(iDetection);
                x_molecule = positions(iDetection);
    
                if x_molecule > 1 && x_molecule < Nx
    
                    x_parabola = x_molecule-1:x_molecule+1;
                    y_parabola = -Y(t_molecule, x_parabola);
    
                    dx_parabolic = (y_parabola(3)-y_parabola(1))/(4*y_parabola(2)-2*y_parabola(1)-2*y_parabola(3));
                    positionsRefined(iDetection) =  x_molecule+dx_parabolic;
    
                end
    
            end
    
        case 'centroid'
    
            for iDetection = 1:nDetections
    
                t_molecule = frames(iDetection);
                x_molecule = positions(iDetection);
    
                if x_molecule > options.fittingRadius && x_molecule < (Nx-options.fittingRadius+1)
    
                    x_centroid = x_molecule-options.fittingRadius:x_molecule+options.fittingRadius;
                    y_centroid = -Y(t_molecule, x_centroid);
    
                    positionsRefined(iDetection) = x_centroid * y_centroid.' / sum(y_centroid);
    
                end
    
            end
    
        case 'gaussian'

            for iDetection = 1:nDetections
    
                t_molecule = frames(iDetection);
                x_molecule = positions(iDetection);
    
                if x_molecule > options.fittingRadius && x_molecule < (Nx-options.fittingRadius+1)
    
                    x_fit = x_molecule-options.fittingRadius:x_molecule+options.fittingRadius;
                    y_fit = -Y(t_molecule, x_fit);
                    
                    f = fit(x_fit.', y_fit.', options.fitType);
                
                    positionsRefined(iDetection) = f.b1;

                end
    
            end

    end

end
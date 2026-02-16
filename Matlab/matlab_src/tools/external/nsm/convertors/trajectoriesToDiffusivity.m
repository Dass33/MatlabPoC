function [diffusivity, velocity] = trajectoriesToDiffusivity(position, timeFrame, tav, fun_flow)

% Estimation of the diffusion coefficient from time series of particle positions
% based on Vestergaard, C. L.;  Blainey, P. C.; Flyvbjerg, H., Optimal estimation of diffusion coefficients from single-particle trajectories. Phys Rev E 2014, 89 (2).

% position - a time serie of measured positions of a particle
% timeFrame - series of particle frames 
% tav - time averaging

% diffusivity - estimated diffusion coefficient corrected for the motion blur and localization error [pixel^2/timeFrame]
% velocity [pixel/timeFrame]

if length(position)>=tav+1

    Dposition = (position(tav+1:end) - position(1:end-tav))./(timeFrame(tav+1:end) - timeFrame(1:end-tav));
    
    if fun_flow==0
        velocity = 0;
        [diffusivity0, ~, notOutlier] = std_modified(Dposition, 0, 1);
    else 
        %velocity = mean(Dposition,  'omitnan');
        [diffusivity0, velocity, notOutlier] = std_modified(Dposition, 1, 1);
        Dposition = Dposition - velocity;
    end
    diffusivity0 = diffusivity0/2;

    Dposition2 = Dposition(1:end-tav).*Dposition(tav+1:end);

    % diffusivity0 = mean(Dposition.^2, 'omitnan')/2;
    % diffusivity = diffusivity0 + mean(Dposition2, 'omitnan');

    notOulier2 = notOutlier(1:end-tav) & notOutlier(tav+1:end);
    correction = mean(Dposition2(notOulier2));

    diffusivity = diffusivity0 + correction;
    
    
else
    
    diffusivity = NaN;
    velocity = NaN;
    
end
    



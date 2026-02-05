function Trajectory = evaluateTrajectory (PARTICLES, I,  property, data, denoise_setting, PT_setting, channel_setting, I0)

[Nt, Nx] = size(I);

Trajectory = struct([]);       

for i=1:length(PARTICLES) 

        [iOC, positionRefined] = analyzeMinimas(I, PARTICLES(i).timeFrame, PARTICLES(i).position, 0);

    if sum(strcmp(property,'iOC')) == 1

        [Trajectory(i).STDiOC, Trajectory(i).iOC, ~] = std_modified(iOC, 1, 1);
        Trajectory(i).iOCprofile_y = iOC/Trajectory(i).iOC;
        Trajectory(i).iOCprofile_x = PARTICLES(i).position;
        
    end

    if sum(strcmp(property,'N')) == 1
        Trajectory(i).N = sum(not(isnan(iOC)));
    end

    if sum(strcmp(property,'D')) == 1
        %[Trajectory(i).D, Trajectory(i).velocity] = trajectoriesToDiffusivity(PARTICLES(i).positionRefined(notOutlier), PARTICLES(i).timeFrame(notOutlier), 1, PT_setting.flowEstimate); 
        [Trajectory(i).D, Trajectory(i).velocity] = trajectoriesToDiffusivity(positionRefined, PARTICLES(i).timeFrame, 1, PT_setting.flowEstimate); 
    end

    if sum(strcmp(property,'I')) == 1
        isRelevant = not(isnan(PARTICLES(i).I));
        [Trajectory(i).STDI, Trajectory(i).I, a] = std_modified(PARTICLES(i).I(isRelevant), 1, 1);
    end

    if sum(strcmp(property,'convertUnits'))==1 && sum(strcmp(property,'iOC'))==1 
        Trajectory(i).iOC = Trajectory(i).iOC*data.Dx;
        Trajectory(i).STDiOC = Trajectory(i).STDiOC*data.Dx;
    end

    % if sum(strcmp(property,'convertUnits'))==1 && sum(strcmp(property,'iOCfit'))==1 
    %     Trajectory(i).iOCfit = Trajectory(i).iOCfit*data.Dx;
    % end

    if sum(strcmp(property,'convertUnits'))==1 && sum(strcmp(property,'D'))==1 
        Trajectory(i).D = Trajectory(i).D*data.Dx^2/data.Dt;
        Trajectory(i).velocity = Trajectory(i).velocity*data.Dx/data.Dt;
    end

    if sum(strcmp(property,'MW'))==1 %molecular weight
        Trajectory(i).MW = iOCToWeight (Trajectory(i).iOC, channel_setting.area, channel_setting.areaWithoutCoating, channel_setting.I_rel, channel_setting.particleMaterial);
    end

    if sum(strcmp(property,'HR'))==1 %hydrodynamic radius
        Trajectory(i).HR = diffusivityToSize (Trajectory(i).D, channel_setting.area);
    end

     % if sum(strcmp(property,'I0'))==1 %mean original intensity
     %    Trajectory(i).I0 = mean(I0(PARTICLES(i).timeFrame,:),'all');
     % end

     

end

    

%     %imagesc(1:size(data.Im,2), 1:size(data.Im,1), data.Im); hold on
%     for i=1:length(indTrajectory)
%         plot(DIPS.position(indTrajectory{i}), DIPS.timeFrame(indTrajectory{i}),'o','Color','white')
%     end

%     %% trajectory characteristics
%     for i=1:length(relevantTrajectory)
%         trajectory(relevantTrajectory(i)) = evaluateTrajectory(PARTICLES(relevantTrajectory(i)), {'iOC','iOC_std','N'});
% %         trajectory(i) = evaluateTrajectory(DIPS, indTrajectory{i}, {'timeFrame','position','N','D','iOC','iOC_std'}, denoise_setting, PT_setting);
% %         trajectory(i).D = unitConversion(trajectory(i).D, data,'px2 per timeFrame to um2 per second');
% %         trajectory(i).iOC = unitConversion(trajectory(i).iOC, data,'px to um');
%     end
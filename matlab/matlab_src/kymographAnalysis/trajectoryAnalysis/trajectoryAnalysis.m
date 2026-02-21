function Trajectory = trajectoryAnalysis (Trajectory, trajectoryProperties, setting, I)

% trajectoryProperties:
%   iOCprofile:     iOC values along the trajectory [um]
%   iOC:            mean iOC across the trajectory [um]
%   STDiOC:         std iOC across the trajectory [um]
%   notOutlier:     outliers in terms of iOC along the trajectory [false/true]
%   positionStart:  minimal spatial position  [pixel]
%   positionEnd:    maximal spatial position  [pixel]
%   N:              number of (notOutlier) frames
%   D:              diffusivity [um2/s]
%   velocity:       [um/s]
%   MW:             molecular weight [Da]
%   HR:             hydrodynamic radius [um]

Np = length(Trajectory.timeFrame);

%% calculate iOC in every trajectory frame (iOCprofile) 
if sum(strcmp(trajectoryProperties,'iOCprofile')) == 1 || sum(strcmp(trajectoryProperties,'iOC')) == 1 ||  sum(strcmp(trajectoryProperties,'STDiOC')) == 1

    Trajectory.iOCprofile = cell(1, Np);

    for i = 1:Np
    
        [Trajectory.iOCprofile{i},~,baseLength] = analyzeMinimas(I, Trajectory.timeFrame{i}, Trajectory.position{i}, 0);
        A = (2*setting.Wx+1)./(2*setting.Wx+1-baseLength);
        Trajectory.iOCprofile{i} = Trajectory.iOCprofile{i}.*A;
        % pixel -> um conversion
        Trajectory.iOCprofile{i} = Trajectory.iOCprofile{i}*setting.Dx;

    end
 
end

%% calculate OC in every trajectory frame and spam 0:setting.Wx
if sum(strcmp(trajectoryProperties,'OCprofile')) == 1 || sum(strcmp(trajectoryProperties,'OC')) == 1 

    Trajectory.OCprofile = cell(1, Np);

    for i = 1:Np

        Trajectory.OCprofile{i} = NaN(length(Trajectory.position{i}), setting.Wx+1);
        for it = 1:length(Trajectory.position{i})

            relevant_t = Trajectory.timeFrame{i}(it);
            relevant_x = Trajectory.position{i}(it);
            Trajectory.OCprofile{i}(it,1) = I(relevant_t, relevant_x);

            for R = 1:setting.Wx
                A = (2*setting.Wx+1)/(2*setting.Wx+1-2*R);
                relevant_x = (Trajectory.position{i}(it) - R):(Trajectory.position{i}(it) + R);
                if sum(relevant_x < 1)==0 && sum(relevant_x > size(I,2))==0
                    Trajectory.OCprofile{i}(it,R+1) = A * trapz(I(relevant_t, relevant_x));
                end
            end

        end
        
        % pixel -> um conversion
        Trajectory.OCprofile{i} = Trajectory.OCprofile{i}*setting.Dx;

    end
end

%% calculate mean OC in every trajectory frame and spam 0:setting.Wx
if sum(strcmp(trajectoryProperties,'OC')) == 1 

    Trajectory.OC = NaN(setting.Wx+1, Np);
    Trajectory.STDOC = NaN(setting.Wx+1, Np);

    for i = 1:Np

        [Trajectory.STDOC(:,i), Trajectory.OC(:,i), ~] = std_modified_ND(Trajectory.OCprofile{i}, 1);

    end
end

%% calculate mean iOC and STDiOC
if sum(strcmp(trajectoryProperties,'iOC')) == 1 ||  sum(strcmp(trajectoryProperties,'STDiOC')) == 1

    Trajectory.STDiOC = NaN(1, Np);
    Trajectory.iOC = NaN(1, Np);
    Trajectory.notOutlier = cell(1, Np);

    for i = 1:Np
        [Trajectory.STDiOC(i), Trajectory.iOC(i), Trajectory.notOutlier{i}] = std_modified(Trajectory.iOCprofile{i}, 1, 1);
    end

end

%% get positionStart and position End
if sum(strcmp(trajectoryProperties,'positionStart')) == 1 || sum(strcmp(trajectoryProperties,'positionEnd')) == 1

    Trajectory.positionStart = NaN(1, Np);
    Trajectory.positionEnd = NaN(1, Np);

    for i = 1:Np
        Trajectory.positionStart(i) = min(Trajectory.positionRefined{i});
        Trajectory.positionEnd(i) = max(Trajectory.positionRefined{i});
    end
end



%% calculate N
if sum(strcmp(trajectoryProperties,'N')) == 1

    Trajectory.N = NaN(1, Np);
    Trajectory.N = NaN(1, Np);

    for i = 1:Np

        if isfield(Trajectory, 'notOutlier')
            Trajectory.N(i) = sum(Trajectory.notOutlier{i});
        else
            Trajectory.N(i) = length(Trajectory.timeFrame{i});
        end
    end

end

%% calculate D and/or velocity
if sum(strcmp(trajectoryProperties,'D')) == 1 || sum(strcmp(trajectoryProperties,'velocity')) == 1

    Trajectory.D = NaN(1, Np);
    Trajectory.velocity = NaN(1, Np);

    for i = 1:Np
       
        [Trajectory.D(i), Trajectory.velocity(i)] = trajectoriesToDiffusivity(Trajectory.positionRefined{i}, Trajectory.timeFrame{i}); 

        % pixel^2/frame -? um^2/s conversion
        Trajectory.D(i) = Trajectory.D(i)*setting.Dx^2/setting.Dt;
        Trajectory.velocity(i) = Trajectory.velocity(i)*setting.Dx/setting.Dt;
    
    end

end


%% calculate molecular weight
if sum(strcmp(trajectoryProperties,'MW'))==1 
    Trajectory.MW = iOCToWeight (Trajectory.iOC, setting.channel.area, setting.channel.areaWithoutCoating, setting.channel.I_rel, setting.channel.particleMaterial);
end

%% calculate hydrodynamic radius
if sum(strcmp(trajectoryProperties,'HR'))==1 
    Trajectory.HR = diffusivityToSize (Trajectory.D, setting.channelArea);
end

% %% remove fields of Trajectory that are not in the list "property"
% fnames = fieldnames(Trajectory);
% for i = 1:length(fnames)
%     if sum(strcmp(property, fnames{i}))==0
%         Trajectory = rmfield(Trajectory,fnames{i});
%     end
% end





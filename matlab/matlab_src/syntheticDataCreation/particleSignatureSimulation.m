function simulated = particleSignatureSimulation(simulated, fun)

%the script simulates optical signatures of particles 

%fun defines particles' movevement
%fun = 'diffusing_molecules'; %multiple molecules only diffusing
%fun = 'flowing_molecules'; %multiple molecules flowing and diffusing
%fun = 'diffusing_in_trap'; % a single molecule diffusing in a trap
%fun = 'flow_direction_change'; %multiple molecules flowing and diffusing, flow changes periodically its drection

%INPUT parameters:
% simulated.D_um2s - diffusivity of a particle [um2/s]
% simulated.Dx - size of one pixel [um]
% simulated.Dt - temporal length of one frame [second]
% simulated.number_frames - number of frames of the simulated kymograph
% simulated.number_pixels - number of pixels of the simulated kymograph
% simulated.number_smooth - number of frames inbetween one time step
% simulated.concentration - mean number of particles in the FOW
% simulated.DLS - size of a diffraction limited step (PSF) [pixel] - exp(-1/2*(x/DLS)^2)

% specific for different fun = 'flowing_molecules'
% simulated.velocity_ums - velocity [um/s]

% specific for different fun = 'flow_direction_change'
% simulated.velocity_ums - [forward velocity, backward velocity] [um/s]
% simulated.timespan_s - duration of [forward movement, backward movement] [seconds]

% OUTPUT parameters
% simulated.responce - particles' optical signature - kymograph without the noise
% simulated.trajectory.position - matrix of particle positions
% simulated.trajectory.timeFrame - matrix of particle positions

%to plot the resulting kymograph use:

% figure;
% imagesc(simulated.responce); hold on
% xlabel('Position')
% ylabel('Time')
% for i=1:length(simulated.trajectory)
%     plot(simulated.trajectory(j).position, simulated.trajectory(j).timeFrame, '.','Color','white');
% end


%%%% 
simulated.D=simulated.D_um2s/simulated.Dx^2*simulated.Dt; %diffusivity [pixel^2/frame]

switch fun

    case 'diffusing_molecules'

        simulated.velocity=0; %[pixels/frame]
        
        space_extention = 5;
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*simulated.velocity : space_extention*simulated.number_pixels;
        simulation_size0 = length(simulation_space);
        particle_number = ceil(simulation_size0/simulated.number_pixels*simulated.concentration);
        simulation_size = particle_number*simulated.number_pixels/simulated.concentration;
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*simulated.velocity - ceil(simulation_size - simulation_size0)/2 : space_extention*simulated.number_pixels + floor(simulation_size - simulation_size0)/2;
 
    case 'flowing_molecules'

        simulated.velocity=simulated.velocity_ums/simulated.Dx*simulated.Dt; %[pixels/frame]
         
        space_extention = 5;
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*simulated.velocity : space_extention*simulated.number_pixels;
        simulation_size0 = length(simulation_space);
        particle_number = ceil(simulation_size0/simulated.number_pixels*simulated.concentration);
        simulation_size = particle_number*simulated.number_pixels/simulated.concentration;
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*simulated.velocity - ceil(simulation_size - simulation_size0)/2 : space_extention*simulated.number_pixels + floor(simulation_size - simulation_size0)/2;


     case 'diffusing_in_trap'

        simulated.velocity=0; %pixels/frame
        
        simulation_space = 31:simulated.number_pixels-30;
        particle_number = 1;
        simulation_size = simulated.number_pixels;
 
    case 'flow_direction_change'
 

        simulated.velocity=simulated.velocity_ums/simulated.Dx*simulated.Dt; %[pixels/frame]
        simulated.timespam = simulated.timespam_s/simulated.Dt; %[frame]
         
        space_extention = 5;
        mean_velocity = (simulated.velocity(1)*simulated.timespam(1) + simulated.velocity(2)*simulated.timespam(2))/sum(simulated.timespam);
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*mean_velocity : space_extention*simulated.number_pixels;
        simulation_size0 = length(simulation_space);
        particle_number = ceil(simulation_size0/simulated.number_pixels*simulated.concentration);
        simulation_size = particle_number*simulated.number_pixels/simulated.concentration;
        simulation_space = -space_extention*simulated.number_pixels-simulated.number_frames*mean_velocity - ceil(simulation_size - simulation_size0)/2 : space_extention*simulated.number_pixels + floor(simulation_size - simulation_size0)/2;
  
end

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
    
%% simulate diffusive movement 
x=sqrt(2*simulated.D/simulated.number_smooth)*...
            randn(particle_number,simulated.number_frames*simulated.number_smooth);

% randomized
% pos0=rand(particle_number,1)*simulation_size + simulation_space(1);


%equidistant
pos0 = linspace(simulation_space(1), simulation_space(end), particle_number + 1);
pos0(end) = [];
pos0 = pos0(:);

pos=cumsum(x,2)+pos0;

%% back-reflected those who are outside the simulation space
for i=1:size(pos,1)
            a = find(pos(i,:)<simulation_space(1) | pos(i,:)>simulation_space(end));
            while isempty(a) == 0
                a = a(1)

%                 close all
%                 plot(pos(i,:),1:size(pos,2)); hold on
%                 plot(simulation_space(1)*ones(1,size(pos,2)),1:size(pos,2),'Color','black');
%                  plot(simulation_space(end)*ones(1,size(pos,2)),1:size(pos,2),'Color','black');

                if pos(i,a)<simulation_space(1)
                    pos(i,a:end) = 2*simulation_space(1) - pos(i,a:end);
                elseif pos(i,a)>simulation_space(end)
                    pos(i,a:end) = 2*simulation_space(end) - pos(i,a:end);
                end
                a = find(pos(i,:)<simulation_space(1) | pos(i,:)>simulation_space(end));

                %plot(pos(i,:),1:size(pos,2)); hold on
            end
end

%% adding the flow
if strcmp(fun,'flowing_molecules') == 1

            pos = pos + simulated.velocity/simulated.number_smooth*[1:size(pos,2)];

elseif strcmp(fun,'flow_direction_change') == 1

            velocity_profile1 = simulated.velocity(1)/simulated.number_smooth*[1:simulated.timespam(1)*simulated.number_smooth];
            velocity_profile2 = simulated.velocity(2)/simulated.number_smooth*[1:simulated.timespam(2)*simulated.number_smooth];

            velocity_profile = 0;
            while length(velocity_profile) < simulated.number_smooth*simulated.number_frames
                velocity_profile = [velocity_profile, velocity_profile1 + velocity_profile(end)];
                velocity_profile = [velocity_profile, velocity_profile2 + velocity_profile(end)];
            end

            velocity_profile = velocity_profile(1:simulated.number_smooth*simulated.number_frames);

            pos = pos + velocity_profile;

end
            

%% select only those in the FOV and create a trajectory
        a = pos>=-3*simulated.DLS & pos<=simulated.number_pixels+3*simulated.DLS;
        T = zeros(size(pos));
        iT = 0;
        for i=1:size(pos,1)
            if a(i,1) == 1 %new trajectory
                iT = iT+1;
                T(i,1) = iT;
            end
            for j=2:size(pos,2)
                if a(i,j) == 1 %trajectory
                    if a(i,j-1) == 0 %new trajectory
                        iT = iT +1;
                    end

                    T(i,j) = iT;
                end
            end
        end

        j = 0;
        simulated.trajectory = [];
        for i=1:iT
            [a,b] = find(T == i);
            b = floor(b(1)/simulated.number_smooth)*simulated.number_smooth + 1 : ceil(b(end)/simulated.number_smooth)*simulated.number_smooth;
            position = pos(a(1),b)';
            if sum(position>=1 & position<=simulated.number_pixels) >= 2*simulated.number_smooth
                
                j = j+1;
                simulated.trajectory(j).position = position;
                simulated.trajectory(j).timeFrame = b';
            end
        end

%         close all
%         plot(pos,1:size(pos,2)); hold on
%         for i=1:length(simulated.trajectory)
%             plot(simulated.trajectory(i).position, simulated.trajectory(i).timeFrame,'.')
%         end
%         plot(1*ones(1,size(pos,2)),1:size(pos,2),'Color','black');
%         plot(simulated.number_pixels*ones(1,size(pos,2)),1:size(pos,2),'Color','black');
%         xlim([simulation_space(1)-100 simulation_space(end)+100])
%         xlabel('Position')
%         ylabel('Frame')


%% construct kymograph (particles' opticla signatures, without the noise)
        simulated.responce=zeros(simulated.number_frames*simulated.number_smooth,simulated.number_pixels);
        x = 1:simulated.number_pixels;

        for i=1:length(simulated.trajectory)

            a = repmat(x,length(simulated.trajectory(i).position),1);
            b = repmat(simulated.trajectory(i).position,1, length(x));
            responce = exp(-1/2*((a-b)/simulated.DLS).^2);
            simulated.responce(simulated.trajectory(i).timeFrame,:) = simulated.responce(simulated.trajectory(i).timeFrame,:) + responce;
        end

%% smooth in time
        simulated.responce = reshape(simulated.responce,simulated.number_smooth,[],length(x));
        simulated.responce = mean(simulated.responce,1);
        simulated.responce = permute(simulated.responce,[2,3,1]);

        for i=1:length(simulated.trajectory)
            simulated.trajectory(i).position = reshape(simulated.trajectory(i).position,simulated.number_smooth,[]);
            simulated.trajectory(i).position = mean(simulated.trajectory(i).position,1);
            simulated.trajectory(i).position = simulated.trajectory(i).position(:);

            simulated.trajectory(i).timeFrame = simulated.trajectory(i).timeFrame(simulated.number_smooth:simulated.number_smooth:end)/simulated.number_smooth;

            %remove poitsn outside the FOV
            a = find(simulated.trajectory(i).position>=1 & simulated.trajectory(i).position<=simulated.number_pixels);
            simulated.trajectory(i).timeFrame = simulated.trajectory(i).timeFrame(a);
            simulated.trajectory(i).position = simulated.trajectory(i).position(a);

        end   
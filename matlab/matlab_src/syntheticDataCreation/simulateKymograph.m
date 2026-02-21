clear;

addpath('/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/nsm-data-analysis/particleAnalysis/Utils')
%addpath('C:\_projects\nsm-data-analysis\particleAnalysis\Utils')

%mainFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/synthetic_data/';
%mainFolder='C:\_projects\nsm-data\synthetic_data\';
mainFolder = '/Volumes/data/Synthetic data/';

%kymographFolder = 'simulated_realistic_background_withoutPositionFluctuation_plus_flowing_molecules';
kymographFolder = 'simulated_realistic_background_plus_flowing_molecules';
%kymographFolder = '2025_09_23_plus_flowing_molecules';

fun_movement = 'flowing_molecules'; %'diffusing_molecules', 'flowing_molecules', 'diffusing_in_trap', 'flow_direction_change'
D_um2s=5;%[10,20,50]; %diffusivity [um^2/s]
%iOC_um=[2e-4,5e-4, 1e-3,2e-3];%[0.5e-4,1e-4,2e-4,5e-4,1e-3,2e-3,5e-3];%,]; %integrated optical contrast [um]
iOC_um=2e-3;%[2e-4, 5e-4, 1e-3, 2e-3, 5e-3, 1e-2];

simulated.Dx =  0.066; %0.0295; %size of one pixel [um] %or will be defined by the experimentl backgrounds
simulated.Dt = 1/142.5; %0.0082; %0.007;%0.0050;temporal length of one frame [second]
simulated.number_frames = 2000; %number of frames of the simulated kymograph
simulated.number_pixels = 464; %number of pixels of the simulated kymograph
simulated.number_smooth = 100; %number of frames inbetween one time step
simulated.concentration = 1; %mean number of particles in the FOW
simulated.DLS = 4; %size of a diffraction limited step (PSF) [pixel] - exp(-1/2*(x/DLS)^2)
simulated.velocity_ums = 15; %0.5*simulated.Dx/simulated.Dt; %[um/s] 600/100*simulated.Dx/simulated.Dt; %[um/s]
% simulated.velocity_timespan_s

N = 50; %number of simulations

%%%%

fun_background = 'simulated'; %simulated, experimental

if strcmp(fun_background, 'experimental')

    NoiseFolder= '/Volumes/data/Synthetic data/Experimental background/2025_09_23/';
    NoiseTimeStamp = findXfiles(NoiseFolder,'.tiff');

elseif strcmp(fun_background, 'simulated')

    simulated.darkSignal.type = 'experimental';

    darkSignalFolder = '/Volumes/data/Measurements/Dark signal calibration/2025-09-23-32pixels/2025_09_23-18_54_22/';
    darkSignalTimeStamp = findXfiles(darkSignalFolder,'.tiff');

    simulated.beamProfile.width = 400;
    simulated.beamProfile.maxIntensity = 80;
    simulated.shotNoise = 1.5e-4;
    simulated.beamProfile.intensityFluctuationSTD = 1e-3;
    simulated.beamProfile.positionFluctuationD = 1e-2; %[pixel^2/frame]

end

%% create kymographFolder
d = dir(strcat(mainFolder)); 
if ~any(strcmp({d.name}, kymographFolder))
    mkdir(mainFolder,kymographFolder);
end


%% create blank
for iN = 1:N

    if strcmp(fun_background,'simulated') == 1

        simulated.darkSignal.file = strcat(darkSignalFolder, '/', darkSignalTimeStamp{mod(iN,length(darkSignalTimeStamp))+1});

        data = simulateBackground(simulated);

    elseif strcmp(fun_background,'experimental') == 1

        filename = strcat(NoiseFolder,'/',NoiseTimeStamp{mod(iN,length(NoiseTimeStamp))+1});
        data = loadRawData(filename, 'tiff2');

        % %load(strcat(NoiseFolder,'/',NoiseTimeStamp{iN},'_M.mat'))
        % %load(strcat(NoiseFolder,'/',NoiseTimeStamp{iN},'.mat'))
        % filename = strcat(NoiseFolder,'/',NoiseTimeStamp{mod(iN,length(NoiseTimeStamp))+1}, '.tiff');
        % info = imfinfo(filename);
        % 
        % data.Im = zeros(info(1).Height, info(1).Width, length(info));
        % for i = 1:size(data.Im,3)
        %     data.Im(:,:,i) = imread(filename, i);
        % end
        % data.Dx = simulated.Dx;
        % data.Dt = simulated.Dt;

    end

    blankPath = strcat(mainFolder,'/',kymographFolder,'/iOC0_D0/iOC0_D0_',num2str(iN),'_M.mat');

    %create folder collection
    d = dir(strcat(mainFolder,'/',kymographFolder)); 
    if ~any(strcmp({d.name}, 'iOC0_D0'))
        mkdir(strcat(mainFolder,'/',kymographFolder),'iOC0_D0');
    end
    save(blankPath,'data')

end



%%

for iD=1:length(D_um2s)
    
    for iiOC=1:length(iOC_um)
        
        for iN=1:N

            %load blank
             blankPath = strcat(mainFolder,'/',kymographFolder,'/iOC0_D0/iOC0_D0_',num2str(iN),'_M.mat');
             load(blankPath)
            
            %load particle signature
            simulated.D_um2s=D_um2s(iD);
            [simulationSizeFolder, simulationName] = contructSimulationName(simulated, iN,fun_movement);
            simulationPath = strcat(mainFolder,'/particleSignatures/',simulationSizeFolder,'/',fun_movement,'/',simulationName,'.mat');
            [status, values] = fileattrib(simulationPath);
            if status == 1
                load(simulationPath)
            else
                simulated = particleSignatureSimulation(simulated, fun_movement);
                save(simulationPath,'simulated');
            end
           
            iOC=iOC_um(iiOC)/simulated.Dx;   
            responce=-iOC/(sqrt(2*pi)*simulated.DLS)*simulated.responce;
            if isfield(data, 'dark')
                data.Im=(data.Im - data.dark) .* (responce+1) + data.dark;
            else
                data.Im=data.Im  .* (responce+1);
            end

            %save kymograph
            kymographPath = strcat(mainFolder,'/',kymographFolder,'/iOC',num2str(iOC_um(iiOC)),'_',simulationName,'_M.mat');
            save(kymographPath,'data')

            
            disp([iD,iiOC,iN])
                
        end
            
            
            
    end

end
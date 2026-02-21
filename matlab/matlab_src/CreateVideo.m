clear;
close all

%ExperimentFolder = '/Volumes/data/Measurements/EVAGELOS/DNA origami/2025-09-23-evagelos-dna-origami/2025_09_23-19_30_14/';
ExperimentFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/FZU/DNA origami/2025-09-23-evagelos-dna-origami/2025_09_23-19_30_14/';
ExperimentTimeStamp = '2025_09_23-19_30_14';

particleAnalysisFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/nsm-data-analysis/particleAnalysis/';  % Baras laptop

% settings relevant to kymograph reconstruction     
setting.ws = 3; %RMS width of point-spread function [pixel]; i.e. corresponds to the parameter ws in particle image profile exp(-0.5*(x/ws).^2)
setting.Wx = 25; %for 1st-pass of kymograph reconstruction, sliding window length for moving average in spatial coordinate for backround estimation [px]
setting.Wt = 25; %for 1st-pass of kymograph reconstruction, sliding window length for moving average in time coordinate for backround estimation [frames]
setting.WxSweep = 25;%[1,10:10:50]; %for 2nd-pass of kymograph reconstruction, span of Wx [px]
setting.WtSweep = 25;%[1, 10:10:50];  %for 2nd-pass of kymograph reconstruction, span of Wt [px]

% if exist - path to the dark signal calibration
% if dark signal calibration does not exist, give an estimate of dark signal (~8)
%setting.darkCalibration = '/Volumes/data/Measurements/Dark signal calibration/2025-09-23-32pixels.mat'; 
setting.darkCalibration = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/FZU/Dark signal calibration/2025-09-23-32pixels.mat';
setting.analysis.Title = 'TwoPassDataProcesing_v01'; 


%% ------------------------------

% %% load raw data
% data = loadRawData(strcat(ExperimentFolder,ExperimentTimeStamp), 'tiff3');
% save(strcat(ExperimentFolder,ExperimentTimeStamp,'_M.mat'), 'data')

%% load M file - data.I
load(strcat(ExperimentFolder,ExperimentTimeStamp,'_M.mat'), 'data')

%% create data.Im - average over y axis of a nanochannel image
data.Im = mean(data.I,1);
data.Im = permute(data.Im, [3,2,1]);

%% analyze data.Im 
addpath(strcat(particleAnalysisFolder, 'kymographReconstruction'))

%% set default setting in two-pass kymograh reconstruction
% related to kymograph reconstruction
if ~isfield(setting.analysis, 'removeBackground_Dark'); setting.analysis.removeBackground_Dark = 'none'; end
if ~isfield(setting.analysis, 'removeBackground_Light_averageX'); setting.analysis.removeBackground_Light_averageX = 'mean'; end % mean, median
if ~isfield(setting.analysis, 'removeBackground_Light_averageT'); setting.analysis.removeBackground_Light_averageT = 'mean'; end % mean, median
if ~isfield(setting.analysis, 'removeBackground_Light_maskX'); setting.analysis.removeBackground_Light_maskX = 'on'; end % on, off
if ~isfield(setting.analysis, 'removeBackground_Light_maskT'); setting.analysis.removeBackground_Light_maskT = 'on'; end % on, off

%% load dark calibration 
if isnumeric(setting.darkCalibration) == 0
    load(setting.darkCalibration)
end

%% Expected characteristics of the particle signatures
%span of the gaussian denoising Kernel [pixel] / expected RMS of particle profile
setting.wx = setting.ws; 
%setting.wx = sqrt(setting.ws.^2 + D_input/3); %this can be expected form diffusing particle with known diffusivity D_input

%minimal distance between spots (must be odd number)
meanRMSWidthAfterConvolution = sqrt(setting.wx.^2 + setting.ws.^2);
meanFWHM = 2*sqrt(2*log(2))* meanRMSWidthAfterConvolution;
%setting.Wm = floor((meanFWHM - 1)/2)*2+1; 
setting.Wm = floor((meanFWHM - 1)/2)*4+1; 

%% first-pass kymograph reconstruction
% Estimate dark-signal profile
if isnumeric(setting.darkCalibration) == 0
    d_x = get_dark_x((data.TemperatureStart + data.TemperatureEnd)/2, Calibration);
else 
    d_x = setting.darkCalibration;
end

% Removal of light and dark background, first estimation of the residual
R1 = data.Im - d_x;
    
 % Matched Filtering for noise reduction
R1_filt = imgaussfilt(R1,[eps, setting.wx+eps],'FilterSize',[1,2*ceil(3*(setting.wx+eps))+1]);  

% Removal of the remaining drifts, first estimation of particle contrast (kymograph)
[C1, resultC1] = removeBackground_Light(R1_filt, setting);
    

%% apply the same for data.I
%removal of dark-signal profile
I = data.I - d_x; 

% Removal of light and dark background, first estimation of the residual
R2 = (I - permute(resultR1.D_t,[3,2,1]))./permute(resultR1.B,[3,2,1]);

% Matched Gaussian Filtering for noise reduction
R2_filt = imgaussfilt(R2,[setting.wx+eps, setting.wx+eps],'FilterSize',[1,2*ceil(3*(setting.wx+eps))+1]);  

%R2_filt = imgaussfilt(R2,[setting.wx+eps, setting.wx+eps, eps],'FilterSize',[1,2*ceil(3*(setting.wx+eps))+1]);  
Et = movmean(R2_filt, 2*setting.Wt + 1, 3);
Ex = movmean(R2_filt./Et, 2*setting.Wx + 1, 2);
epsilon = Ex.*Et;
C2 = (R2_filt - epsilon)./permute(resultC1.epsilon,[3,2,1]);


%% plot kymograph
figure
imagesc(C1);
colormap bone

%% plot nanochannel image
figure
imagesc(I(:,:,1));
colormap bone
axis equal

figure
imagesc(imgaussfilt(I(:,:,1),[setting.wx+eps, setting.wx+eps],'FilterSize',[1,2*ceil(3*(setting.wx+eps))+1]));  
colormap bone
axis equal

%% plot nanochannel image
for i=660:680
    figure
    imagesc(C2(:,:,i));
    colormap bone
    axis equal
end

%% create a video
framesToPrint = 450:800;
for idx = 1:length(framesToPrint)
    %figure('Color',[0 0 0],'Position',[600 600-250 1000 300]);
    close all
    figure('Color',[0 0 0]);
    
    imagesc(C2(:,:,framesToPrint(idx))); 
    colormap(bone)
    caxis([min(C2,[],'all'), max(C2,[],'all')])
    xlim([1, size(C2,2)])
    ylim([1, size(C2,1)])
    axis off
    axis equal

    drawnow
    frame = getframe(1);
    im{idx} = frame2im(frame);
end
close;
%%
movie_file = strcat(ExperimentFolder,ExperimentTimeStamp,'.gif');

for idx = 1:length(im)
    [B,map] = rgb2ind(im{idx},256);
    if idx == 1
        imwrite(B,map,movie_file,'gif','LoopCount',Inf,'DelayTime',1);
    else
        imwrite(B,map,movie_file,'gif','WriteMode','append','DelayTime',0.05);
    end
end





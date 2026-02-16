%% MH, v2.9, 2025_10_17

%% init
close all
clear, clc

addpath(genpath('tools'))
set(0, 'DefaultLineLineWidth', 1);
rng("default")

%% control

evaluateFolder = true;
% evaluateFolder = false;

exportImages = true;
% exportImages = false;

%% paths

rawDataFilePath = fullfile('demo_data','2025-05-13-dna-origami','2025_05_13-20_55_03.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-05-13-evagelos-dna-origami','2025_05_13-20_55_03','2025_05_13-20_55_03.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-07-04-taha-thyroglobulin','2025_07_04-18_31_42','2025_07_04-18_33_37.tiff');
% rawDataFilePath = fullfile('..','..','data','2025-07-04-taha-thyroglobulin','2025_07_04-18_31_42','2025_07_04-18_33_30.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-08-27-taha-thyroglobulin2.0','2025_09_04-17_02_14','2025_09_04-17_04_08.tiff');
% rawDataFilePath = fullfile('..','..','data','2025-08-27-taha-thyroglobulin2.0','2025_09_04-17_02_14','2025_09_04-17_02_23.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-04-01-yulia-urease','2025_04_01-12_27_37','2025_04_01-12_29_43.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-09-23-evagelos-dna-origami','2025_09_23-17_55_16','2025_09_23-17_55_16.tiff');
% rawDataFilePath = fullfile('..','..','data','2025-09-23-evagelos-dna-origami','2025_09_23-19_38_43','2025_09_23-19_38_43.tiff');

% rawDataFilePath = fullfile('..','..','data','2025-09-24-evagelos-dna-origami','2025_09_24-19_34_38','2025_09_24-19_34_38.tiff');
% rawDataFilePath = fullfile('..','..','data','2025-09-24-evagelos-dna-origami','2025_09_24-20_57_01','2025_09_24-20_57_01.tiff');

[folderPath,fileName,~] = fileparts(rawDataFilePath);
[~,folderName,~] = fileparts(folderPath);
fileNames = getFileNamesInFolder(folderPath);
% [~,parentFolderName,~] = fileparts(fileparts(folderPath));

exportFolderPath = fullfile('demo_export', folderName);
% exportFolderPath = fullfile('export', parentFolderName, folderName);

%% preprocessing parameters

% Kt = 51;
Kt = 159;

%% denoising parameters

% spaceFilter = 'gaussian';
% sigma_x = 2;

% spaceFilter = 'laplacean_of_gaussian';
% sigma_x = 5.3;

spaceFilter = 'jinc';
sigma_x = 2.97; 

% timeFilter = 'none';
timeFilter = 'imgaussfilt';
sigma_t = 1.19;

nonLinearFilter = 'none';
% nonLinearFilter = 'nlm';

%% detector parameters

% false alarm probability
% pfa = 1e-2;
% pfa = 1e-3;
% pfa = 1e-4;
pfa = 1e-5;
% pfa = 1e-6;

localMinRange = 6;

%% feature extraction parameters

positionRefinementMethod = 'centroid';
fittingRadius = 3;

%% linking parameters

% spot linking parameters

% cut_off_distance = 15;
cut_off_distance = 20;

unmatched_penalty_distance = 15;
% unmatched_penalty_distance = 20;
% unmatched_penalty_distance = 25;
% unmatched_penalty_distance = 30;

flowEstimate = 0;
% flowEstimate = -2;
% flowEstimate = -3;
% flowEstimate = -5;
% flowEstimate = -6;
% flowEstimate = -10;
% flowEstimate = -15;

% gab closing parameters

% maxPositiveGab = 1;
% maxPositiveGab = 2;
maxPositiveGab = 3;
% maxPositiveGab = 4;

% maxNegativeGab = 1;
maxNegativeGab = 2;

% gab_closing_cut_off_distance = 30;
gab_closing_cut_off_distance = 40;
% gab_closing_cut_off_distance = 50;

gab_closing_penalty_distance = 30;
% gab_closing_penalty_distance = 40;

% linking postprocessing

% minTrackLength = 20;
% minTrackLength = 30;
minTrackLength = 40;

%% load raw data
R = imread(rawDataFilePath);

Nt = size(R,1);

% showKymograph(R, title='raw')

%% preprocessing
X = preprocessing(R, Kt=Kt);

% showKymograph(-X, title='preprocessed')

%% denoising
Y = denoising(X, ...
    spaceFilter=spaceFilter, ...
    sigma_x=sigma_x, ...
    timeFilter=timeFilter, ...
    sigma_t=sigma_t, ...
    nonLinearFilter=nonLinearFilter);

% showKymograph(-Y, title='denoised')

%% detection
Detections = detection(Y, pfa=pfa, localMinRange=localMinRange);

showKymograph(-Y, ...
    title=['detections, mean snr=', num2str(mean(Detections.snr),3)], ...
    detections=Detections, ...
    detectionsIntensitySign='-')

%% contrast image

Contrast.chainOrder = 'preprocessing_denoising';

Contrast.defluctuationMethod = 'mean';
Contrast.Kx = 1; 
Contrast.bacgroundEstimationMethod = 'movmean';
Contrast.Kt = 159; 
Contrast.backgroundRemovalMethod = 'subtract_divide';
Contrast.whiteningMethod = 'std_division';

Contrast.spaceFilter = 'jinc';
Contrast.sigma_x = 2.97;
Contrast.k_max = 2;

C = preprocessingDenoising(R, ...
    chainOrder=Contrast.chainOrder, ...
    defluctuationMethod=Contrast.defluctuationMethod, ...
    Kx=Contrast.Kx, ...
    bacgroundEstimationMethod=Contrast.bacgroundEstimationMethod, ...
    Kt=Contrast.Kt, ...
    backgroundRemovalMethod=Contrast.backgroundRemovalMethod, ...
    whiteningMethod=Contrast.whiteningMethod, ...
    spaceFilter=Contrast.spaceFilter, ...
    sigma_x=Contrast.sigma_x, ...
    k_max=Contrast.k_max ...
);

showKymograph(-C, title='contrast')

%% position refinment
Detections.position_refined = refinement(Detections.position, Detections.frame, C, ...
    method=positionRefinementMethod, fittingRadius=fittingRadius);

%% contrast
Detections.contrast = C(sub2ind(size(C), Detections.frame, Detections.position));

%% table with detected spots
Spots = makeSpotTable(Detections);

%% frame-by-frame spot linking
Edges = spotLinking(Spots, Nt, cut_off_distance, unmatched_penalty_distance, flowEstimate);

%% table with spot linking edges
EdgesTable = makeEdgeTable(Edges);

%% jump distance histogram
figure;
% histogram(EdgesTable.jump_distance)
histogram(EdgesTable.jump_distance, Normalization="pdf")
title( ['jump distance histogram, mean = ', num2str(mean(EdgesTable.jump_distance),3)] )
xlabel('jump distance')
ylabel('occurence')
hold on
plotGaussianFit(EdgesTable.jump_distance)

%% join linked spots into tracklets
Tracklets = joinLinkedSpots(EdgesTable, Spots);

showKymograph(-Y, Tracks=Tracklets, detectionsIntensitySign='-', title='tracklets');

%% table with tracklets
TrackletsTable = makeTrackletTable(Tracklets);

%% linking tracklets to close the gabs
[matchedTrackletIds, unmatchedRows] = trackletLinking(TrackletsTable, maxNegativeGab, maxPositiveGab, ...
    gab_closing_cut_off_distance, gab_closing_penalty_distance);

%% join linked tracklets into tracks
RawTracks = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets);

showKymograph(-Y, Tracks=RawTracks, detectionsIntensitySign='-', title='raw tracks');

%% delete track spots with non-positive gabs
Tracks = deleteSpotsWithNonPositiveGabs(RawTracks);

% showKymograph(-Y, Tracks=Tracks, detectionsIntensitySign='-', title='non-negative-gabs tracks');

%% track postprocessing to filter short tracks
FinalTracks = trackPostprocessing(Tracks, minTrackLength);

showKymograph(-Y, Tracks=FinalTracks, detectionsIntensitySign='-', title='final tracks');

% showKymograph(-Y, Tracks=FinalTracks, detectionsIntensitySign='-', ...
%     xlabel='space [px]', ...
%     ylabel='time [frames]', ...
%     showColorbar=false, ...
%     exportFigure=true, ...
%     alpha=0.5, ...
%     view='xyz', ...
%     exportName='gab_closing_tracks'...
%     );

%% histogram of jump distances
% if FinalTracks.nTracks>0
%     FinalTracks.jumps = cellfun(@diff,FinalTracks.positions,'UniformOutput',false);
%     jumps = vertcat( FinalTracks.jumps{ 1:FinalTracks.nTracks });
% 
%     figure;
%     histogram(jumps, 30)
%     title(['mean jumps = ', num2str(mean(jumps),3)])
% end

%% process all files in folder 

if evaluateFolder

    tic

    for iFile = progress(1:length(fileNames))
    % for iFile = progress(1:2)

        rawDataFilePath = fullfile( folderPath, [fileNames{iFile}, '.tiff'] );

        spt(rawDataFilePath, Contrast, ...
            Kt=Kt, ...
            spaceFilter=spaceFilter, ...
            sigma_x=sigma_x,...
            timeFilter=timeFilter, ...
            sigma_t=sigma_t, ...
            nonLinearFilter=nonLinearFilter, ...
            pfa=pfa, ...
            localMinRange=localMinRange, ...
            positionRefinementMethod=positionRefinementMethod, ...
            fittingRadius=fittingRadius, ...
            cut_off_distance=cut_off_distance,...
            unmatched_penalty_distance=unmatched_penalty_distance,...
            flowEstimate=flowEstimate, ...
            maxNegativeGab=maxNegativeGab, ...
            maxPositiveGab=maxPositiveGab, ...
            gab_closing_cut_off_distance=gab_closing_cut_off_distance, ...
            gab_closing_penalty_distance=gab_closing_penalty_distance, ...
            minTrackLength=minTrackLength, ...
            exportImages=exportImages,...
            exportFolderPath=exportFolderPath ...
            );

    end

    toc

end

%% init
close all
clear, clc

addpath(genpath('tools'))
set(0, 'DefaultLineLineWidth', 1);
rng("default")

%% control

evaluateFolder = true;

exportImages = true;

%% paths

rawDataFilePath = fullfile('demo_data','2025-05-13-dna-origami','2025_05_13-20_55_03.tiff');


[folderPath,fileName,~] = fileparts(rawDataFilePath);
[~,folderName,~] = fileparts(folderPath);
fileNames = getFileNamesInFolder(folderPath);

exportFolderPath = fullfile('demo_export', folderName);

%% preprocessing parameters

Kt = 159;

%% denoising parameters

spaceFilter = 'jinc';
sigma_x = 2.97; 

timeFilter = 'imgaussfilt';
sigma_t = 1.19;

nonLinearFilter = 'none';

%% detector parameters

% false alarm probability
pfa = 1e-5;

localMinRange = 6;

%% feature extraction parameters

positionRefinementMethod = 'centroid';
fittingRadius = 3;

%% linking parameters

% spot linking parameters

cut_off_distance = 20;
unmatched_penalty_distance = 15;
flowEstimate = 0;

% gab closing parameters

maxPositiveGab = 3;
maxNegativeGab = 2;
gab_closing_cut_off_distance = 40;
gab_closing_penalty_distance = 30;

% linking postprocessing
minTrackLength = 40;

%% load raw data
R = imread(rawDataFilePath);

Nt = size(R,1);

%% preprocessing
X = preprocessing(R, Kt=Kt);

%% denoising
Y = denoising(X, ...
    spaceFilter=spaceFilter, ...
    sigma_x=sigma_x, ...
    timeFilter=timeFilter, ...
    sigma_t=sigma_t, ...
    nonLinearFilter=nonLinearFilter);

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

%% process all files in folder 

if evaluateFolder

    tic

    for iFile = progress(1:length(fileNames))

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

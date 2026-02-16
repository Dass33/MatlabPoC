function analyze_image(inputDir, outputDir, options)
% ANALYZE_IMAGE Wrapper: Processes all TIFFs in inputDir and saves results to outputDir.

arguments
  inputDir char
  outputDir char

  % --- Preprocessing Parameters ---
  options.Kt (1,1) double = 159

  % --- Denoising Parameters ---
  options.spaceFilter char = 'jinc'
  options.sigma_x (1,1) double = 2.97
  options.timeFilter char = 'imgaussfilt'
  options.sigma_t (1,1) double = 1.19
  options.nonLinearFilter char = 'none'

  % --- Detection Parameters ---
  options.pfa (1,1) double = 1e-5
  options.localMinRange (1,1) double = 6

  % --- Feature Extraction Parameters ---
  options.positionRefinementMethod char = 'centroid'
  options.fittingRadius (1,1) double = 3

  % --- Contrast Image Parameters ---
  options.Contrast_chainOrder char = 'preprocessing_denoising'
  options.Contrast_defluctuationMethod char = 'mean'
  options.Contrast_Kx (1,1) double = 1
  options.Contrast_bacgroundEstimationMethod char = 'movmean'
  options.Contrast_Kt (1,1) double = 159
  options.Contrast_backgroundRemovalMethod char = 'subtract_divide'
  options.Contrast_whiteningMethod char = 'std_division'
  options.Contrast_spaceFilter char = 'jinc'
  options.Contrast_sigma_x (1,1) double = 2.97
  options.Contrast_k_max (1,1) double = 2

  % --- Linking Parameters ---
  options.cut_off_distance (1,1) double = 20
  options.unmatched_penalty_distance (1,1) double = 15
  options.flowEstimate (1,1) double = 0
  options.maxPositiveGab (1,1) double = 3
  options.maxNegativeGab (1,1) double = 2
  options.gab_closing_cut_off_distance (1,1) double = 40
  options.gab_closing_penalty_distance (1,1) double = 30
  options.minTrackLength (1,1) double = 40
end

% Setup paths
% file_path = fileparts(mfilename('fullpath'));
% addpath(genpath(fullfile(file_path, 'tools')));

if ~exist(outputDir, 'dir'); mkdir(outputDir); end

% Get all TIFF files
files = dir(fullfile(inputDir, '*.tif*'));

for i = 1:numel(files)
  fileName = files(i).name;
  inputFile = fullfile(files(i).folder, fileName);
  [~, name, ~] = fileparts(fileName);
  outputFile = fullfile(outputDir, [name '.mat']);

  process_single_tiff(inputFile, outputFile, options);
end
end

function process_single_tiff(inputFile, outputFile, options)
% Load specific TIFF file (handles multi-page stacks)
R = double(imread(inputFile));

Nt = size(R, 1);

% 1. Preprocessing
X = preprocessing(R, Kt=options.Kt);

% 2. Denoising
Y = denoising(X, ...
  spaceFilter=options.spaceFilter, ...
  sigma_x=options.sigma_x, ...
  timeFilter=options.timeFilter, ...
  sigma_t=options.sigma_t, ...
  nonLinearFilter=options.nonLinearFilter);

% 3. Detection
Detections = detection(Y, ...
  pfa=options.pfa, ...
  localMinRange=options.localMinRange);

% 4. Contrast Image
C = preprocessingDenoising(R, ...
  chainOrder=options.Contrast_chainOrder, ...
  defluctuationMethod=options.Contrast_defluctuationMethod, ...
  Kx=options.Contrast_Kx, ...
  bacgroundEstimationMethod=options.Contrast_bacgroundEstimationMethod, ...
  Kt=options.Contrast_Kt, ...
  backgroundRemovalMethod=options.Contrast_backgroundRemovalMethod, ...
  whiteningMethod=options.Contrast_whiteningMethod, ...
  spaceFilter=options.Contrast_spaceFilter, ...
  sigma_x=options.Contrast_sigma_x, ...
  k_max=options.Contrast_k_max ...
  );

% 5. Position Refinement
Detections.position_refined = refinement(Detections.position, Detections.frame, C, ...
  method=options.positionRefinementMethod, ...
  fittingRadius=options.fittingRadius);

% 6. Contrast Extraction
if ~isempty(Detections.frame)
  Detections.contrast = C(sub2ind(size(C), Detections.frame, Detections.position));
else
  Detections.contrast = [];
end

% 7. Tracking / Linking
Spots = makeSpotTable(Detections);
Edges = spotLinking(Spots, Nt, options.cut_off_distance, options.unmatched_penalty_distance, options.flowEstimate);
EdgesTable = makeEdgeTable(Edges);
Tracklets = joinLinkedSpots(EdgesTable, Spots);
TrackletsTable = makeTrackletTable(Tracklets);

[matchedTrackletIds, unmatchedRows] = trackletLinking(TrackletsTable, ...
  options.maxNegativeGab, options.maxPositiveGab, ...
  options.gab_closing_cut_off_distance, options.gab_closing_penalty_distance);

RawTracks = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets);
Tracks = deleteSpotsWithNonPositiveGabs(RawTracks);
FinalTracks = trackPostprocessing(Tracks, options.minTrackLength);

% Save Result
save(outputFile, 'FinalTracks', 'Detections', 'Y', 'C', '-v7.3');
end

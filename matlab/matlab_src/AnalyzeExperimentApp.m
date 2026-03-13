function AnalyzeExperimentApp(inputDir, outputDir)
% App entry point for the AnalyzeExperiment pipeline.
%
statusFile = fullfile(outputDir, 'status.json');

try
  if ~exist(outputDir, 'dir')
    mkdir(outputDir);
  end

  write_status(statusFile, 'processing', '');

  % ── Headless ──────────────────────────────────────────────────────────
  set(0, 'DefaultFigureVisible', 'off');

  % ── Load config ───────────────────────────────────────────────────────
  configFile = fullfile(inputDir, '..', 'config.json');
  if ~exist(configFile, 'file')
    error('config.json not found at: %s', configFile);
  end
  config = jsondecode(fileread(configFile));

  Setting = build_setting(config, outputDir);

  [collection, inputDataInfo] = kymographAnalysis(inputDir, Setting);

  makeFolderIfNotExisting(fullfile(outputDir, 'collection'));
  save( fullfile(outputDir,'collection','collection'), 'collection');

  collection = setfield(collection, {1}, 'positionStart', []);
  collection = setfield(collection, {1}, 'positionEnd', []);
  for iSweep = 1:length(collection)
    collection(iSweep) = trajectoryAnalysis(collection(iSweep), 'positionStart', [], []);
    collection(iSweep) = trajectoryAnalysis(collection(iSweep), 'positionEnd', [], []);
  end

  makeFolderIfNotExisting(fullfile(outputDir, 'analysis'));

  plotProperties = {'iOC', 'D', 'STDiOC','velocity','N','positionStart', 'positionEnd'}; % select from collection fields

  for iSweep = 1:length(collection)
    figScatterPlots = figure('Name', collection(iSweep).SweepLegend);
    scatterPlotCollection(collection(iSweep), plotProperties, '.');

    exportgraphics( figScatterPlots, fullfile(outputDir,'analysis','scatterPlot.png'),'Resolution',Setting.exportDpi );
    saveas( figScatterPlots, fullfile(outputDir,'analysis','scatterPlot.fig') );

  end

  % ── Collection postprocessing ─────────────────────────────────────────
  for iSweep = 1:length(collection)
    [collectionPostprocessed(iSweep), collectionCalibrated(iSweep)] = collectionPostprocessing(collection(iSweep), Setting);
  end


  save( fullfile(outputDir,'collection','collection_postprocessed'), 'collectionPostprocessed' )

  plotProperties = [Setting.outlierFiltering.referenceProperty, Setting.outlierFiltering.filterProperties];

  for iSweep = 1:length(collectionPostprocessed)
    figOutliers = figure('Name', collection(iSweep).SweepLegend, ...
      'Position', [0 0 760 453]);
    scatterPlotCollection(collection(iSweep), plotProperties, '.');
    scatterPlotCollection(collectionCalibrated(iSweep), plotProperties, '.', collectionCalibrated(iSweep).threshold);
    scatterPlotCollection(collectionPostprocessed(iSweep), plotProperties, 'o');
    legend({'collection', 'collection calibrated','lower threshold','upper threshold','collection postprocessed'})

    exportgraphics( figOutliers, fullfile(outputDir,'analysis','outliers.png'),'Resolution',Setting.exportDpi );
    saveas( figOutliers, fullfile(outputDir,'analysis','outliers.fig') );

  end

  if strcmp(Setting.iOCcalibration,'on')
    for iSweep = 1:length(collectionCalibrated)

      figCalibration = figure('Name', collection(iSweep).SweepLegend);

      subplot(1,3,1)
      plot(collectionCalibrated(iSweep).calibration.x,collectionCalibrated(iSweep).calibration.A); hold on
      xlabel('x')
      ylabel('A')

      subplot(1,3,2)
      plot(collectionCalibrated(iSweep).calibration.x, collectionCalibrated(iSweep).calibration.Astd); hold on
      xlabel('x')
      ylabel('Astd')

      subplot(1,3,3)
      plot(collectionCalibrated(iSweep).calibration.x, collectionCalibrated(iSweep).calibration.AN); hold on
      xlabel('x')
      ylabel('AN')

      exportgraphics( figCalibration, fullfile(outputDir,'analysis','calibration.png'),'Resolution',Setting.exportDpi );
      saveas( figCalibration, fullfile(outputDir,'analysis','calibration.fig') );

    end
  end

  % ── Population analysis ───────────────────────────────────────────────
  for iSweep = 1:length(collection)
    if strcmp(Setting.populationAnalysis.Title, 'GMM')
      population(iSweep) = analyzePopulation_GMM(collectionPostprocessed(iSweep), Setting.populationAnalysis);
    else
      population(iSweep) = analyzePopulation_robustMean(collectionPostprocessed(iSweep), Setting.populationAnalysis);
    end
  end

  save(fullfile(outputDir,'collection','collection_population'), 'population' )

  % ── Plot population within the scatterplot ────────────────────────────
  for iSweep = 1:length(collectionPostprocessed)
    figClusterAnalysis = figure('Name', collection(iSweep).SweepLegend, ...
      'Position', [0 0 790 476]);

    scatterPlotCollection(collectionPostprocessed(iSweep), ...
      Setting.populationAnalysis.properties, 'Nweighted', population(iSweep));

    exportgraphics( figClusterAnalysis, fullfile(outputDir,'analysis','clusterAnalysis.png'),'Resolution',Setting.exportDpi );
    saveas( figClusterAnalysis, fullfile(outputDir,'analysis','clusterAnalysis.fig') );

  end

  %% plot MEAN, FWHM, RESOLUTION values as dependency on Sweep
  plotProperty = 'iOC';

  noSweep = 1:length(collectionPostprocessed);
  MEAN = [population.MEAN];
  MEAN = [MEAN.(plotProperty)];
  FWHM = [population.FWHM];
  FWHM = [FWHM.(plotProperty)];
  RESOLUTION = [population.RESOLUTION];
  RESOLUTION = [RESOLUTION.(plotProperty)];

  figSweep = figure('Position', [0 0 960 620]);

  subplot(3,1,1)
  plot(noSweep, MEAN)
  xlabel('Sweep no')
  ylabel(strcat(plotProperty, ' MEAN'))
  xticks(noSweep)
  xticklabels({collectionPostprocessed.SweepLegend})

  subplot(3,1,2)
  plot(noSweep, FWHM)
  xlabel('Sweep no')
  ylabel(strcat(plotProperty, ' FWHM'))
  xticks(noSweep)
  xticklabels({collectionPostprocessed.SweepLegend})

  subplot(3,1,3)
  plot(noSweep, RESOLUTION)
  xlabel('Sweep no')
  ylabel(strcat(plotProperty, ' RESOLUTION'))
  xticks(noSweep)
  xticklabels({collectionPostprocessed.SweepLegend})

  exportgraphics( figSweep, fullfile(outputDir,'analysis','sweep.png'),'Resolution',Setting.exportDpi );
  saveas( figSweep, fullfile(outputDir,'analysis','sweep.fig') );

  % convert collection to table of analysis

  Analysis.file_name = collectionPostprocessed.ExperimentTimeStamp;

  % Analysis.positions = cellfun(@round, collectionPostprocessed.positionRefined, 'UniformOutput', false);
  Analysis.positions_refined = collectionPostprocessed.positionRefined;
  Analysis.frames = collectionPostprocessed.timeFrame;
  Analysis.iOCs = collectionPostprocessed.iOCprofile;

  Analysis.mean_D = collectionPostprocessed.D;
  Analysis.mean_iOC = collectionPostprocessed.iOC;
  Analysis.std_iOC = collectionPostprocessed.STDiOC;
  Analysis.velocity_ums = collectionPostprocessed.velocity;
  Analysis.length = collectionPostprocessed.N;

  Analysis.position_start = collectionPostprocessed.positionStart;
  Analysis.position_end = collectionPostprocessed.positionEnd;

  Analysis = structfun(@transpose, Analysis, 'UniformOutput', false);

  Analysis = struct2table(Analysis);

  save( fullfile(outputDir,'Analysis.mat'), 'Analysis');

  writestruct(Setting, fullfile(outputDir,'Setting.json' ), FileType='json');
  save_summary(outputDir, population, collectionPostprocessed, Setting.populationAnalysis.properties);
  close all
  write_status(statusFile, 'completed', '');

catch ME
  write_status(statusFile, 'failed', ME.message);
end

end % AnalyzeExperimentApp


% ─────────────────────────────────────────────────────────────────────────────

function Setting = build_setting(config, outputDir)

% Paths
Setting.Path.exportFolder = outputDir;
Setting.Path.projectFolder = fileparts(fileparts(mfilename('fullpath')));

% Export
Setting.exportDpi = 150;
Setting.exportOptinalFigures = config.exportOptionalFigures;

% Acquisition
Setting.Dt              = config.Dt;
Setting.Dx              = config.Dx;
Setting.flipIntensity   = config.flipIntensity;
Setting.flowEstimate    = config.flowEstimate;
Setting.flowEstimate_ums = Setting.Dx / Setting.Dt * Setting.flowEstimate;

if isfield(config, 'inputDataFormat')
  Setting.inputDataFormat = config.inputDataFormat;
else
  Setting.inputDataFormat = 'tiff2';
end

% Kymograph preprocessing
Setting.kymographPreprocessing = config.kymographPreprocessing;

% Detection
Setting.Detection = config.Detection;
Setting.Detection.boarderRange = Setting.Detection.localOptimumRange;

% Feature extraction
Setting.FeatureExtraction.positionRefinementMethod = 'centroid';
Setting.FeatureExtraction.fittingRadius = Setting.Detection.localOptimumRange;

% Trajectory detection algorithm
valid_trackers = {'gabClosingTracker', 'trackBeforeDetect'};
if isfield(config, 'tracker') && ismember(config.tracker, valid_trackers)
  Setting.trajectoryDetecton.Title = config.tracker;
else
  Setting.trajectoryDetecton.Title = 'gabClosingTracker';
end

if strcmp(Setting.trajectoryDetecton.Title, 'trackBeforeDetect')
  Setting.Tlength        = config.Tlength;
  Setting.thresholdLimit = config.thresholdLimit;
  Setting.TmaxNo         = config.TmaxNo;
end

% Linking
Setting.Linking = config.Linking;
Setting.Linking.flowEstimate_ums = Setting.flowEstimate_ums;
Setting.Linking.showTrackIds = true;

% Kymograph analysis
Setting.kymographAnalysis.Title          = 'OnePassKymographAnalysis';
Setting.kymographAnalysis.plotKymograph  = 'off';
Setting.kymographAnalysis.saveKymograph  = 'png';

% jsondecode gives Nx1 cell for JSON string arrays; transpose to 1xN
Setting.kymographAnalysis.trajectoryProperties = config.trajectoryProperties.';

% Post-processing
Setting.iOCcalibration = config.iOCcalibration;
Setting.outlierFiltering.referenceProperty  = config.outlierFiltering.referenceProperty;
Setting.outlierFiltering.filterProperties   = config.outlierFiltering.filterProperties.';
Setting.outlierFiltering.thresholdDirection = config.outlierFiltering.thresholdDirection.';
Setting.outlierFiltering.thresholdValue     = config.outlierFiltering.thresholdValue.';

% Population analysis
Setting.populationAnalysis.Title      = config.populationAnalysis.Title;
Setting.populationAnalysis.properties = config.populationAnalysis.properties.';

end % build_setting


% ─────────────────────────────────────────────────────────────────────────────

function save_summary(outputDir, population, collectionPostprocessed, properties)
% Write population statistics per sweep to summary.json.

sweeps = cell(1, length(population));
for iSweep = 1:length(population)
  pop = population(iSweep);
  s.legend        = collectionPostprocessed(iSweep).SweepLegend;
  s.nTrajectories = pop.Ntrajectories;
  for i = 1:length(properties)
    prop = properties{i};
    s.MEAN.(prop)       = pop.MEAN.(prop);
    s.STD.(prop)        = pop.STD.(prop);
    s.FWHM.(prop)       = pop.FWHM.(prop);
    s.RESOLUTION.(prop) = pop.RESOLUTION.(prop);
  end
  sweeps{iSweep} = s;
end

summary.sweeps = sweeps;
jsonStr = jsonencode(summary);

fid = fopen(fullfile(outputDir, 'summary.json'), 'w');
if fid == -1
  error('save_summary: could not open summary.json for writing in %s', outputDir);
end
fprintf(fid, '%s', jsonStr);
fclose(fid);

end % save_summary


% ─────────────────────────────────────────────────────────────────────────────
function write_status(statusFile, status, errorMsg)

s.status = status;
if isempty(errorMsg)
  s.error = [];
else
  s.error = errorMsg;
end
jsonStr = [jsonencode(s) newline];

tmpFile = [statusFile '.tmp'];
fid = fopen(tmpFile, 'w');
if fid == -1
  error('write_status: could not open %s for writing', tmpFile);
end
fprintf(fid, '%s', jsonStr);
fclose(fid);
movefile(tmpFile, statusFile, 'f');

end % write_status

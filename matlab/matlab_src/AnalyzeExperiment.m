% mh, v3.6, 2026_02_20
%
% Script 'analyzeExperiment' is the main file for the data analysis in
% Nanofluidic Scattering Microscopy (NSM).
%
% Save your modified file with the experimental data on NAS

%% init
close all
clear, clc

%% control

loadSettingFromFile = true;
% loadSettingFromFile = false;

exportOptinalFigures = true;
% exportOptinalFigures = false;

%% paths

% projectFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/nsm-data-analysis/';  % Baras laptop
projectFolder = '.'; % Mirek

% path to the folder with raw kymographs; experiment = set of kymographs = 1 folder
experimentFolder = fullfile('data','demo_data','2025-09-23-dna-origami');

settingFile = fullfile('data','analysis', 'Setting.json');

%% load packages
addpath(genpath(projectFolder));

%% export setting

% analysisName = 'demo';
analysisName = 'Wx15_Wt50';

% exportParentFolder = fullfile( experimentFolder, 'export' );

[~,experimentFolderName,~] = fileparts(experimentFolder);

exportFolder = fullfile( 'data','export', experimentFolderName, analysisName );

makeFolderIfNotExisting(exportFolder);

% processing parameters

if loadSettingFromFile

    Setting = jsondecode( fileread( settingFile ) );

    % transpose issue with json and cell array
    Setting.kymographAnalysis.trajectoryProperties = Setting.kymographAnalysis.trajectoryProperties.';
    Setting.outlierFiltering.filterProperties = Setting.outlierFiltering.filterProperties.';
    Setting.outlierFiltering.thresholdDirection = Setting.outlierFiltering.thresholdDirection.';
    Setting.outlierFiltering.thresholdValue = Setting.outlierFiltering.thresholdValue.';
    Setting.populationAnalysis.properties = Setting.populationAnalysis.properties.';

else

    % paths
    Setting.Path.projectFolder = projectFolder;
    Setting.Path.experimentFolder = experimentFolder;
    Setting.Path.exportFolder = exportFolder;

    % export

    % Setting.exportDpi = 75; % faster, low res
    Setting.exportDpi = 150; % normal
    % Setting.exportDpi = 300; % slower, high res

    Setting.exportOptinalFigures = exportOptinalFigures;
    Setting.flipIntensity = true;

    % acquisition

    % Setting.inputDataFormat = 'tiff1'; % for data saved before 23/09/2025
    Setting.inputDataFormat = 'tiff2'; % for data saved after 23/09/2025
    % Setting.inputDataFormat = 'mat'; % for synthetic data put .mat

    Setting.Dt = 0.007; % frame duration in sec
    Setting.Dx = 0.066; % pixel size in um

    % kymograph preprocessing settings

    %'/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/FZU/Dark signal calibration/2025-09-23-32pixels.mat';
    % path to Dark signal calibration or a number (estimation of dark signal)
    Setting.kymographPreprocessing.darkCalibration = 8;

    %(span of) sliding window(s) length for moving average in spatial coordinate for backround estimation [px]
    Setting.kymographPreprocessing.Wx = 15;

    %(span of) sliding window(s) length for moving average in time coordinate for backround estimation [frames]
    Setting.kymographPreprocessing.Wt = 50;

    % RMS width of point-spread function [pixel]; i.e. corresponds to the parameter ws in particle
    % image profile exp(-0.5*(x/ws).^2)

    % Setting.kymographPreprocessing.ws = 2;
    Setting.kymographPreprocessing.ws = 2.36;
    % Setting.kymographPreprocessing.ws = 3;

    % flow

    % Setting.flowEstimate_ums = -15; % in um/s
    % Setting.flowEstimate_ums = 20;
    % Setting.flowEstimate = Setting.Dt/Setting.Dx * Setting.flowEstimate_ums; % in px/frame

    Setting.flowEstimate = -3.4;
    Setting.flowEstimate_ums = Setting.Dx/Setting.Dt * Setting.flowEstimate;

    % particle tracking setting, more info in trackBeforeDetect.m or gabClosingTracker.m

    % Setting.trajectoryDetecton.Title = 'trackBeforeDetect'; %'trackBeforeDetect' or 'gabClosingTracker'
    Setting.trajectoryDetecton.Title = 'gabClosingTracker';

    Setting.Linking.minTrackLength = 10;
    % Setting.Linking.minTrackLength = 30;

    switch Setting.trajectoryDetecton.Title

        case 'trackBeforeDetect'

            % sets the temporal length of the feature associations, options: 2, 4, 8, 16, 32, 64

            Setting.Tlength = 4;
            % Setting.Tlength = 8;
            % Setting.Tlength = 16;
            % Setting.Tlength = 32;

            % intensity threshold above which all the feature associations are assumed to be noise

            % Setting.thresholdLimit = -1;
            Setting.thresholdLimit = -2;
            % Setting.thresholdLimit = -3;
            % Setting.thresholdLimit = -3.5;
            % Setting.thresholdLimit = -4;

            Setting.TmaxNo = 8; % maximal number of combination of feature associations for each feature (intensity dip)

        case 'gabClosingTracker'

            Setting.Detection.peakSign = 'negative'; % 'negative','positive', 'negative-positive'

            Setting.Detection.pfa = 1e-5;
            Setting.Detection.localOptimumRange = 6;
            Setting.Detection.boarderRange = Setting.Detection.localOptimumRange;

            Setting.FeatureExtraction.positionRefinementMethod = 'centroid';
            Setting.FeatureExtraction.fittingRadius = Setting.Detection.localOptimumRange;

            Setting.Linking.cut_off_distance = 20;
            Setting.Linking.unmatched_penalty_distance = 15;
            Setting.Linking.flowEstimate_ums = Setting.flowEstimate_ums;
            Setting.Linking.maxPositiveGab = 3;
            Setting.Linking.maxNegativeGab = 2;
            Setting.Linking.gab_closing_cut_off_distance = 40;
            Setting.Linking.gab_closing_penalty_distance = 30;

            Setting.Linking.showTrackIds = true;

    end

    % kymograph analysis settings

    Setting.kymographAnalysis.Title = 'OnePassKymographAnalysis'; % 'OnePassKymographAnalysis' or 'TwoPassKymographProcesing'

    Setting.kymographAnalysis.plotKymograph = 'off'; % options: off, on
    Setting.kymographAnalysis.saveKymograph = 'png'; % options: off, png, fig

    Setting.kymographAnalysis.trajectoryProperties = {'positionRefined','timeFrame','iOCprofile','N','iOC','STDiOC','D','velocity'}; % select from the list in trajectoryAnalysis.m

    % outlierFiltering settings, more info in findTrajectoryOutliers.m

    Setting.outlierFiltering.referenceProperty =  'iOC';
    Setting.outlierFiltering.filterProperties =   {'STDiOC', 'velocity', 'N', 'positionStart', 'positionEnd'}; % select from collection fields
    Setting.outlierFiltering.thresholdDirection = {'upper', 'both', 'lower', 'upper', 'lower'}; % upper, lower, or both
    Setting.outlierFiltering.thresholdValue =     {'3std' , '3std', '3std', '3std', '3std'}; % 3std, 3std_conditional, or numeric value(s)

    Setting.iOCcalibration = 'on'; % on or off

    % population analysis
    Setting.populationAnalysis.Title = 'robustMean'; % GMM, robustMean
    Setting.populationAnalysis.properties = {'iOC', 'D','velocity'};

end

%% kymograph analysis

% run kymograph analysis
% [collection, Setting.inputDataInfo] = kymographAnalysis(experimentFolder, Setting);
[collection, ~] = kymographAnalysis(experimentFolder, Setting);

close

makeFolderIfNotExisting( fullfile(exportFolder,'collection') );

save( fullfile(exportFolder,'collection','collection'), 'collection')
% save( fullfile(exportFolder,'collection','collection_setting'), 'Setting')

disp('kymograph analysis finished, collection file saved. continue with analyses of the collection');

%% (example) add addition trajectory property (if needed), that was not in the
% Setting.kymographAnalysis.trajectoryProperties, e.g. positionStart, positionEnd)

collection = setfield(collection, {1},'positionStart', []);
collection = setfield(collection, {1}, 'positionEnd', []);
for iSweep = 1:length(collection)
    collection(iSweep) = trajectoryAnalysis( collection(iSweep), 'positionStart', [], [] );
    collection(iSweep) = trajectoryAnalysis( collection(iSweep), 'positionEnd', [], [] );
end

%% plot collection

makeFolderIfNotExisting( fullfile(exportFolder,'analysis') );

plotProperties = {'iOC', 'D', 'STDiOC','velocity','N','positionStart', 'positionEnd'}; % select from collection fields

for iSweep = 1:length(collection)
    figScatterPlots = figure('Name', collection(iSweep).SweepLegend);
    scatterPlotCollection(collection(iSweep), plotProperties, '.');

    exportgraphics( figScatterPlots, fullfile(exportFolder,'analysis','scatterPlot.png'),'Resolution',Setting.exportDpi );
    saveas( figScatterPlots, fullfile(exportFolder,'analysis','scatterPlot.fig') );

end

%% collection postprocessing
clear collectionPostprocessed collectionCalibrated

for iSweep = 1:length(collection)
    [collectionPostprocessed(iSweep), collectionCalibrated(iSweep)] = collectionPostprocessing(collection(iSweep), Setting);
end

% save postprocessed collection
save( fullfile(exportFolder,'collection','collection_postprocessed'), 'collectionPostprocessed' )
% save( fullfile(exportFolder,'collection','collection_postprocessed_setting'), 'Setting')

%% plot postprocessed collection
plotProperties = [Setting.outlierFiltering.referenceProperty, Setting.outlierFiltering.filterProperties];

for iSweep = 1:length(collectionPostprocessed)
    figOutliers = figure('Name', collection(iSweep).SweepLegend);
    scatterPlotCollection(collection(iSweep), plotProperties, '.');
    scatterPlotCollection(collectionCalibrated(iSweep), plotProperties, '.', collectionCalibrated(iSweep).threshold);
    scatterPlotCollection(collectionPostprocessed(iSweep), plotProperties, 'o');
    legend({'collection', 'collection calibrated','lower threshold','upper threshold','collection postprocessed'})

    exportgraphics( figOutliers, fullfile(exportFolder,'analysis','outliers.png'),'Resolution',Setting.exportDpi );
    saveas( figOutliers, fullfile(exportFolder,'analysis','outliers.fig') );

end

%% plot calibration

if strcmp(Setting.iOCcalibration,'on')
    for iSweep = 1:length(collectionCalibrated)

        figCalibration = figure('Name', collectionCalibrated(iSweep).SweepLegend);

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

        exportgraphics( figCalibration, fullfile(exportFolder,'analysis','calibration.png'),'Resolution',Setting.exportDpi );
        saveas( figCalibration, fullfile(exportFolder,'analysis','calibration.fig') );

    end
end

%% population analysis

clear population

for i = 1:length(collection)
    if strcmp(Setting.populationAnalysis.Title, 'GMM')
        population(i) = analyzePopulation_GMM(collectionPostprocessed(i), Setting.populationAnalysis);
    elseif strcmp(Setting.populationAnalysis.Title, 'robustMean')
        population(i) = analyzePopulation_robustMean(collectionPostprocessed(i), Setting.populationAnalysis);
    end
end

% save population
save( fullfile(exportFolder,'collection','collection_population'), 'population' )
% save( fullfile(exportFolder,'collection','collection_population_setting'), 'Setting')

%% plot population within the scatterplot
for iSweep = 1:length(collectionPostprocessed)

    figClusterAnalysis = figure('Name', collection(iSweep).SweepLegend);
    scatterPlotCollection(collectionPostprocessed(iSweep), ...
        Setting.populationAnalysis.properties, 'Nweighted', population(iSweep));

    exportgraphics( figClusterAnalysis, fullfile(exportFolder,'analysis','clusterAnalysis.png'),'Resolution',Setting.exportDpi );
    saveas( figClusterAnalysis, fullfile(exportFolder,'analysis','clusterAnalysis.fig') );

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

figSweep = figure;

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

exportgraphics( figSweep, fullfile(exportFolder,'analysis','sweep.png'),'Resolution',Setting.exportDpi );
saveas( figSweep, fullfile(exportFolder,'analysis','sweep.fig') );

%% convert collection to table of analysis
clear Analysis

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

disp( Analysis )

%% export table of analysis
% writetable( Analysis, fullfile(exportFolder,'Analysis.csv') );
% writetable( Analysis, fullfile(exportFolder,'Analysis.xlsx') );
% writetable( Analysis, fullfile(exportFolder,'Analysis.txt') );

save( fullfile(exportFolder,'Analysis.mat'), 'Analysis');

%% export Setting as json file
writestruct(Setting, fullfile( exportFolder,'Setting.json' ), FileType='json');

%%
close all

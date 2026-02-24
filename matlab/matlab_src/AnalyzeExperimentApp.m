function AnalyzeExperimentApp(inputDir, outputDir)
% ANALYZEEXPERIMENTAPP  App entry point for the AnalyzeExperiment pipeline.
%
% Reads inputDir/../config.json, builds the Setting struct, runs
% kymographAnalysis → collectionPostprocessing → analyzePopulation, and
% writes structured outputs to outputDir.
%
% Outputs written to outputDir/
%   status.json        — {status, error}
%   kymographs/*.png   — kymograph images with track overlays
%   trajectories.mat   — flat scalar arrays per trajectory (scipy-readable v7)
%   summary.json       — population stats per sweep
%   results.mat        — full archive (v7.3)

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

    % ── Build Setting ─────────────────────────────────────────────────────
    Setting = build_setting(config, outputDir);

    % ── Add paths (source mode only) ──────────────────────────────────────
    if ~isdeployed
        addpath(genpath(Setting.Path.projectFolder));
    end

    % ── Kymograph analysis ────────────────────────────────────────────────
    [collection, inputDataInfo] = kymographAnalysis(inputDir, Setting);

    % ── Add positionStart + positionEnd (always computed separately, never
    %    via trajectoryProperties passed to kymographAnalysis)
    if ~isfield(collection, 'positionStart')
        collection = setfield(collection, {1}, 'positionStart', []);
    end
    if ~isfield(collection, 'positionEnd')
        collection = setfield(collection, {1}, 'positionEnd', []);
    end
    for iSweep = 1:length(collection)
        collection(iSweep) = trajectoryAnalysis(collection(iSweep), 'positionStart', [], []);
        collection(iSweep) = trajectoryAnalysis(collection(iSweep), 'positionEnd', [], []);
    end

    % ── Collection postprocessing ─────────────────────────────────────────
    for iSweep = 1:length(collection)
        if isfield(collection(iSweep), 'iOC') && isempty(collection(iSweep).iOC)
            error('No trajectories detected (sweep %d/%d). Check your data and detection parameters (pfa, flowEstimate).', iSweep, length(collection));
        end
        [collectionPostprocessed(iSweep), collectionCalibrated(iSweep)] = ...
            collectionPostprocessing(collection(iSweep), Setting);
    end

    % ── Population analysis ───────────────────────────────────────────────
    for iSweep = 1:length(collection)
        if strcmp(Setting.populationAnalysis.Title, 'GMM')
            population(iSweep) = analyzePopulation_GMM( ...
                collectionPostprocessed(iSweep), Setting.populationAnalysis);
        else
            population(iSweep) = analyzePopulation_robustMean( ...
                collectionPostprocessed(iSweep), Setting.populationAnalysis);
        end
    end

    % ── Save outputs ──────────────────────────────────────────────────────
    save_trajectories(outputDir, collectionPostprocessed);
    save_summary(outputDir, population, collectionPostprocessed, ...
        Setting.populationAnalysis.properties);
    save(fullfile(outputDir, 'results.mat'), ...
        'collection', 'collectionPostprocessed', 'collectionCalibrated', ...
        'population', 'inputDataInfo', '-v7.3');

    write_status(statusFile, 'completed', '');

catch ME
    write_status(statusFile, 'failed', ME.message);
end

end % AnalyzeExperimentApp


% ─────────────────────────────────────────────────────────────────────────────

function Setting = build_setting(config, outputDir)

validate_config(config);

% Paths
Setting.Path.exportFolder = outputDir;
% In deployed mode addpath is a no-op, but the field must still exist
Setting.Path.projectFolder = fileparts(fileparts(mfilename('fullpath')));

% Export
Setting.exportDpi = 150;
Setting.exportOptinalFigures = false;

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

% Feature extraction (not user-configurable)
Setting.FeatureExtraction.positionRefinementMethod = 'centroid';
Setting.FeatureExtraction.fittingRadius = Setting.Detection.localOptimumRange;

% Trajectory detection algorithm (configurable; defaults to gabClosingTracker)
valid_trackers = {'gabClosingTracker', 'trackBeforeDetect'};
if isfield(config, 'tracker') && ismember(config.tracker, valid_trackers)
    Setting.trajectoryDetecton.Title = config.tracker;
else
    Setting.trajectoryDetecton.Title = 'gabClosingTracker';
end

% Linking
Setting.Linking = config.Linking;
Setting.Linking.flowEstimate_ums = Setting.flowEstimate_ums;
Setting.Linking.showTrackIds = true;

% Kymograph analysis (hardcoded titles)
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

function save_trajectories(outputDir, collectionPostprocessed)
% Concatenate per-sweep trajectory scalars into flat arrays (scipy v7 compatible).

iOC           = [];
D             = [];
velocity      = [];
N             = [];
positionStart = [];
positionEnd   = [];
sweepIdx      = [];
sweepLegends  = {};

for iSweep = 1:length(collectionPostprocessed)
    c = collectionPostprocessed(iSweep);
    n = length(c.iOC);

    iOC           = [iOC;           c.iOC(:)];           %#ok<AGROW>
    D             = [D;             c.D(:)];             %#ok<AGROW>
    velocity      = [velocity;      c.velocity(:)];      %#ok<AGROW>
    N             = [N;             c.N(:)];             %#ok<AGROW>
    positionStart = [positionStart; c.positionStart(:)]; %#ok<AGROW>
    positionEnd   = [positionEnd;   c.positionEnd(:)];   %#ok<AGROW>
    sweepIdx      = [sweepIdx;      iSweep * ones(n, 1)]; %#ok<AGROW>
    sweepLegends{end+1} = c.SweepLegend;                %#ok<AGROW>
end

save(fullfile(outputDir, 'trajectories.mat'), ...
    'iOC', 'D', 'velocity', 'N', 'positionStart', 'positionEnd', ...
    'sweepIdx', 'sweepLegends', '-v7');

end % save_trajectories


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

function validate_config(config)

required_top = {'Dt','Dx','flipIntensity','flowEstimate', ...
    'kymographPreprocessing','Detection','Linking', ...
    'trajectoryProperties','iOCcalibration','outlierFiltering','populationAnalysis'};
for i = 1:length(required_top)
    if ~isfield(config, required_top{i})
        error('config.json missing required field: %s', required_top{i});
    end
end

numeric_fields = {'Dt','Dx','flowEstimate'};
for i = 1:length(numeric_fields)
    f = numeric_fields{i};
    if ~isnumeric(config.(f))
        error('config.json field "%s" must be numeric, got %s', f, class(config.(f)));
    end
end

det_required = {'peakSign','pfa','localOptimumRange'};
for i = 1:length(det_required)
    if ~isfield(config.Detection, det_required{i})
        error('config.json missing required field: Detection.%s', det_required{i});
    end
end
if ~isnumeric(config.Detection.pfa)
    error('config.json field "Detection.pfa" must be numeric, got %s', class(config.Detection.pfa));
end

link_required = {'minTrackLength','cut_off_distance','unmatched_penalty_distance', ...
    'maxNegativeGab','maxPositiveGab','gab_closing_cut_off_distance','gab_closing_penalty_distance'};
for i = 1:length(link_required)
    if ~isfield(config.Linking, link_required{i})
        error('config.json missing required field: Linking.%s', link_required{i});
    end
end

preproc_required = {'Wx','Wt','ws','darkCalibration'};
for i = 1:length(preproc_required)
    if ~isfield(config.kymographPreprocessing, preproc_required{i})
        error('config.json missing required field: kymographPreprocessing.%s', preproc_required{i});
    end
end
if ~isnumeric(config.kymographPreprocessing.Wx)
    error('config.json field "kymographPreprocessing.Wx" must be numeric, got %s', class(config.kymographPreprocessing.Wx));
end
if ~isnumeric(config.kymographPreprocessing.Wt)
    error('config.json field "kymographPreprocessing.Wt" must be numeric, got %s', class(config.kymographPreprocessing.Wt));
end

if isempty(config.trajectoryProperties)
    error('config.json field "trajectoryProperties" must be non-empty');
end

if ~ischar(config.iOCcalibration) || ~ismember(config.iOCcalibration, {'on','off'})
    error('config.json field "iOCcalibration" must be "on" or "off", got: %s', mat2str(config.iOCcalibration));
end

outfilt_required = {'referenceProperty','filterProperties','thresholdDirection','thresholdValue'};
for i = 1:length(outfilt_required)
    if ~isfield(config.outlierFiltering, outfilt_required{i})
        error('config.json missing required field: outlierFiltering.%s', outfilt_required{i});
    end
end

if ~isfield(config.populationAnalysis, 'Title')
    error('config.json missing required field: populationAnalysis.Title');
end
if ~isfield(config.populationAnalysis, 'properties')
    error('config.json missing required field: populationAnalysis.properties');
end
if isempty(config.populationAnalysis.properties)
    error('config.json field "populationAnalysis.properties" must be non-empty');
end

end % validate_config


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

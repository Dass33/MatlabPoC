function analyze_image(inputDir, outputDir)
% ANALYZE_IMAGE Wrapper: Processes all TIFFs in inputDir and saves results to outputDir.
%
% Configuration is read from config.json in the job root (inputDir/../config.json).
% Default values for all parameters are defined in the Streamlit frontend.
%
% Writes outputDir/status.json throughout execution:
%   {"status": "processing", "error": null}    — on start
%   {"status": "completed",  "error": null}    — on success
%   {"status": "failed",     "error": "<msg>"} — on any error

statusFile = fullfile(outputDir, 'status.json');

try
    if ~exist(outputDir, 'dir')
        mkdir(outputDir);
    end

    write_status(statusFile, 'processing', '');

    % ── Load config ───────────────────────────────────────────────────────
    configFile = fullfile(inputDir, '..', 'config.json');
    if ~exist(configFile, 'file')
        error('config.json not found at: %s', configFile);
    end
    config = jsondecode(fileread(configFile));

    % ── Find input files ──────────────────────────────────────────────────
    files = dir(fullfile(inputDir, '*.tif*'));
    if isempty(files)
        error('No TIFF files found in input directory: %s', inputDir);
    end

    nFiles     = numel(files);
    fileErrors = cell(nFiles, 1);

    parfor i = 1:nFiles
        fileName   = files(i).name;
        inputFile  = fullfile(files(i).folder, fileName);
        [~, name, ~] = fileparts(fileName);
        outputFile = fullfile(outputDir, [name '.mat']);

        try
            process_single_tiff(inputFile, outputFile, config);
            fileErrors{i} = '';
        catch ME
            fileErrors{i} = sprintf('%s: %s', fileName, ME.message);
        end
    end

    % ── Aggregate errors ──────────────────────────────────────────────────
    failed = fileErrors(~cellfun(@isempty, fileErrors));

    if isempty(failed)
        write_status(statusFile, 'completed', '');
    else
        write_status(statusFile, 'failed', strjoin(failed, ' | '));
    end

catch ME
    write_status(statusFile, 'failed', ME.message);
end

end % analyze_image


% ─────────────────────────────────────────────────────────────────────────────

function process_single_tiff(inputFile, outputFile, config)

R  = double(imread(inputFile));
Nt = size(R, 1);

% 1. Preprocessing
X = preprocessing(R, Kt=config.Kt);

% 2. Denoising
Y = denoising(X, ...
    spaceFilter     = config.spaceFilter, ...
    sigma_x         = config.sigma_x, ...
    timeFilter      = config.timeFilter, ...
    sigma_t         = config.sigma_t, ...
    nonLinearFilter = config.nonLinearFilter);

% 3. Detection
Detections = detection(Y, ...
    pfa           = config.pfa, ...
    localMinRange = config.localMinRange);

% 4. Contrast Image — parameters are internal pipeline constants, not user-configurable
C = preprocessingDenoising(R, ...
    chainOrder                  = 'preprocessing_denoising', ...
    defluctuationMethod         = 'mean', ...
    Kx                          = 1, ...
    bacgroundEstimationMethod   = 'movmean', ...
    Kt                          = config.Kt, ...
    backgroundRemovalMethod     = 'subtract_divide', ...
    whiteningMethod             = 'std_division', ...
    spaceFilter                 = config.spaceFilter, ...
    sigma_x                     = config.sigma_x, ...
    k_max                       = 2);

% 5. Position Refinement
Detections.position_refined = refinement( ...
    Detections.position, Detections.frame, C, ...
    method        = config.positionRefinementMethod, ...
    fittingRadius = config.fittingRadius);

% 6. Contrast Extraction
if ~isempty(Detections.frame)
    Detections.contrast = C(sub2ind(size(C), Detections.frame, Detections.position));
else
    Detections.contrast = [];
end

% 7. Tracking / Linking
Spots          = makeSpotTable(Detections);
Edges          = spotLinking(Spots, Nt, ...
                     config.cut_off_distance, ...
                     config.unmatched_penalty_distance, ...
                     config.flowEstimate);
EdgesTable     = makeEdgeTable(Edges);
Tracklets      = joinLinkedSpots(EdgesTable, Spots);
TrackletsTable = makeTrackletTable(Tracklets);

[matchedTrackletIds, unmatchedRows] = trackletLinking(TrackletsTable, ...
    config.maxNegativeGab, config.maxPositiveGab, ...
    config.gab_closing_cut_off_distance, ...
    config.gab_closing_penalty_distance);

RawTracks   = joinLinkedTracklets(matchedTrackletIds, unmatchedRows, Tracklets);
Tracks      = deleteSpotsWithNonPositiveGabs(RawTracks);
FinalTracks = trackPostprocessing(Tracks, config.minTrackLength);

save(outputFile, 'FinalTracks', 'Detections', 'Y', 'C', '-v7.3');

end % process_single_tiff


% ─────────────────────────────────────────────────────────────────────────────

function write_status(statusFile, status, errorMsg)
% WRITE_STATUS  Atomically write a status.json understood by the Streamlit frontend.
%
%   status   — 'processing' | 'completed' | 'failed'
%   errorMsg — empty string when not applicable

if isempty(errorMsg)
    jsonStr = sprintf('{"status": "%s", "error": null}\n', status);
else
    safe    = strrep(errorMsg, '\', '\\');
    safe    = strrep(safe,     '"', '\"');
    jsonStr = sprintf('{"status": "%s", "error": "%s"}\n', status, safe);
end

% Write to a temp file then rename for atomicity
tmpFile = [statusFile '.tmp'];
fid = fopen(tmpFile, 'w');
if fid == -1
    warning('write_status: could not open %s for writing', tmpFile);
    return
end
fprintf(fid, '%s', jsonStr);
fclose(fid);
movefile(tmpFile, statusFile, 'f');

end % write_status

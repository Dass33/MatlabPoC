function [notOutlier, threshold] = findTrajectoryOutliers(collection, setting, plotResult)

% This script performs outlier detection and filtering of multidimensional trajectory data 
% extracted from NSM kymographs. 
%
% The goal is to identify and remove trajectories that are likely to correspond to false 
% positives or artefacts, such as:
%   - trajectories affected by optical instabilities -> i.e. high STDiOC, velocities exhibits extreme values relative to the remaining data,
%   - incorrectly connected trajectories, crossing trajectories -> i.e. high STDiOC
%   - background noise incorrectly identified as a particle, noise-induced detections -> i.e. low N
%   - truncated trajectory -> i.e. low N
%
% The filtering is fully configurable by the user with respect to:
%   (i) which trajectory properties are used for filtering, 
%   (ii) whether outliers are defined as values below, above, or outside
%        a threshold range,
%   (iii) how the threshold is determined.
%
% -------------------------------------------------------------------------
% INPUTS
% -------------------------------------------------------------------------
% collection : 
%   Structure containing trajectory properties as fields 
%
% setting: 
%   User-defined configuration describing how outliers are detected.
%
%   setting.referenceProperty
%    String specifying the trajectory property used to condition the threshold,
%    e.g., 'iOC'. Thresholds for the filteringProperties can be computed as a
%    function of this reference property (see below.
%
%   setting.filterProperties
%       Cell array of strings specifying which trajectory properties are
%       used for filtering (e.g. {'N','STDiOC'}).
%
%   filterConfig.thresholdDirection
%       Defines how thresholds are applied. Possible values:
%           'lower'  : reject values below the threshold
%           'upper'  : reject values above the threshold
%           'both'   : reject values outside lower and upper thresholds
%
%   filterConfig.thresholdValue
%       Method used to compute thresholds. Possible values:
%           '3std'              : threshold is computed as 3 standard deviation from the mean
%           '3std_conditional'  : threshold is computed as a linear dependency on referenceProperty (e.g., iOC) 
%                                   (heteroscedastic thresholding)
%           numeric             : user-defined numeric threshold(s), [lower and/or upper]
%           
%
% -------------------------------------------------------------------------
% OUTPUTS
% -------------------------------------------------------------------------
% filteredCollection : struct
%   Structure identical in format to the input collection, but containing
%   only trajectories that pass all filtering criteria.
%
% outlierMask : logical array
%   Logical vector indicating rejected trajectories (true = outlier,
%   false = retained).
%
% thresholds : struct
%   Structure containing the computed threshold values for each filtered
%   property, allowing traceability and reproducibility of the filtering.
%
% -------------------------------------------------------------------------
% DESCRIPTION
% -------------------------------------------------------------------------
% For each selected trajectory property, the script computes the relevant
% threshold(s) according to the chosen method and applies the specified
% directional criterion. Trajectories failing any of the criteria are
% classified as outliers and removed from further analysis.
%
% This modular approach enables transparent, reproducible, and
% physics-informed outlier rejection in multidimensional single-trajectory
% datasets.
%
% -------------------------------------------------------------------------


if nargin < 3
    plotResult = false;
end

plotSubResult = false;

rProperty = setting.referenceProperty;
fProperties = setting.filterProperties;

NfProperties = length(fProperties);
Ntrajectories = length(collection.(rProperty));

% if ~isfield(collection, 'positionStart') && any(strcmp(fProperties, 'positionStart'))
% 
%     collection.positionStart = NaN(1,Ntrajectories);
%     collection.positionEnd = NaN(1,Ntrajectories);
% 
%     for i = 1:length(collection.positionRefined)
%         collection.positionStart(i) = min(collection.positionRefined{i});
%         collection.positionEnd(i) = max(collection.positionRefined{i});
%     end
% 
% end


%% iteratively find outliers from multidimensional data

kk = 0;
notOutlier = cell(NfProperties,1);
for i = 1:NfProperties
    notOutlier{i} = ~isnan(collection.(fProperties{i}));
end
notOutlier = cell2mat(notOutlier);
notOutlier = sum(notOutlier,1) == size(notOutlier,1);
notOutlier0 = not(notOutlier);

while sum(notOutlier ~= notOutlier0) > 0 

    notOutlier0 = notOutlier;

    kk = kk + 1;

    notOutlier = cell(NfProperties,1);
    for i = 1:NfProperties

        % calculate threshold value
        if strcmp(setting.thresholdValue{i}, '3std') || strcmp(setting.thresholdValue{i}, '3std_conditional') 

            if strcmp(setting.thresholdValue{i}, '3std')

                a = collection.(fProperties{i});
                a = a(:,notOutlier0);
                MEAN.(fProperties{i}) = mean(a,2);
                STD.(fProperties{i}) = std(a,1,2);

            elseif strcmp(setting.thresholdValue{i}, '3std_conditional') 

                y = collection.(fProperties{i});
                x = collection.(rProperty);
                MEAN.(fProperties{i}) = ones(size(y));
                STD.(fProperties{i}) = ones(size(y));
                for j = 1:size(y,1)
                    p = [x(1,notOutlier0)', ones(sum(notOutlier0),1)] \ y(j,notOutlier0)';
                    c = y(j,notOutlier0)./(p(1)*x(1,notOutlier0) + p(2));
                    MEAN.(fProperties{i})(j,:) = mean(c).*(p(1)*x(1,:) + p(2));
                    STD.(fProperties{i})(j,:) = std(c).*(p(1)*x(1,:) + p(2));
                end

            end

            if strcmp(setting.thresholdDirection{i}, 'both') 

                threshold.lower.(fProperties{i}) = MEAN.(fProperties{i}) - 3*STD.(fProperties{i});
                threshold.upper.(fProperties{i}) = MEAN.(fProperties{i}) + 3*STD.(fProperties{i});

            elseif strcmp(setting.thresholdDirection{i}, 'lower') 

                threshold.lower.(fProperties{i}) = MEAN.(fProperties{i}) - 3*STD.(fProperties{i});
                threshold.upper.(fProperties{i}) = Inf(size(MEAN.(fProperties{i})));

            elseif strcmp(setting.thresholdDirection{i}, 'upper') 

                threshold.lower.(fProperties{i}) = -Inf(size(MEAN.(fProperties{i})));
                threshold.upper.(fProperties{i}) = MEAN.(fProperties{i}) + 3*STD.(fProperties{i});

            end
  

        else

            if strcmp(setting.thresholdDirection{i}, 'both') 

                threshold.lower.(fProperties{i}) = setting.thresholdValue{i}(1);
                threshold.upper.(fProperties{i}) = setting.thresholdValue{i}(2);

            elseif strcmp(setting.thresholdDirection{i}, 'lower')  

                threshold.lower.(fProperties{i}) = setting.thresholdValue{i}(1);
                threshold.upper.(fProperties{i}) = Inf;

            elseif strcmp(setting.thresholdDirection{i}, 'upper') 

                threshold.lower.(fProperties{i}) = -Inf;
                threshold.upper.(fProperties{i}) = setting.thresholdValue{i}(1);

            end

        end

    
        notOutlier{i} = collection.(fProperties{i}) < threshold.upper.(fProperties{i}) & collection.(fProperties{i}) > threshold.lower.(fProperties{i});

    end

    notOutlier = cell2mat(notOutlier);
    notOutlier = sum(notOutlier,1) == size(notOutlier,1);

    if plotSubResult
        scatterPlotCollection(collection, [rProperty, fProperties], '.'); 
        scatterPlotCollection(collection, [rProperty, fProperties], 'o', threshold, notOutlier);
    end
        

    %disp(sum(notOutlier ~= notOutlier0))
end


if plotResult

    figure('Name', collection.SweepLegend)
    scatterPlotCollection(collection, [rProperty, fProperties], '.'); 
    scatterPlotCollection(collection, [rProperty, fProperties], 'o', threshold, notOutlier);
end

% %% filter out outliers
% collection_filtered = collection;
% fnames = fieldnames(collection);
% for i = 1:length(fnames)
%     if length(collection.(fnames{i})) == length(notOutlier)
%         collection_filtered.(fnames{i}) = collection.(fnames{i})(notOutlier);
%     end
% end




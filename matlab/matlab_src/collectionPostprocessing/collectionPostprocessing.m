function [collectionFiltered, collectionCalibrated] = collectionPostprocessing(collection, setting)

plotSubResult = false;


if strcmp(setting.iOCcalibration, 'off')


    %% find outliers
    [notOutlier, threshold] = findTrajectoryOutliers(collection, setting.outlierFiltering, plotSubResult);

    calibration = '';
    collectionCalibrated = collection;

else

    %% find outliers and calibrate
    Ntrajectories = length(collection.iOC);
    
    notOutlier0 = false(1, Ntrajectories);
    notOutlier = true(1,Ntrajectories);
    collectionCalibrated = collection;
    
    
    while sum(notOutlier ~= notOutlier0) > 0
    
        notOutlier0 = notOutlier;
    
        [notOutlier, threshold] = findTrajectoryOutliers(collectionCalibrated, setting.outlierFiltering, plotSubResult);
    
        if strcmp(setting.iOCcalibration, 'on')
            calibration = iOCcalibration(collectionCalibrated.iOCprofile(notOutlier), collectionCalibrated.positionRefined(notOutlier), plotSubResult);
        elseif strcmp(setting.iOCcalibration, 'OC')
            calibration = OCcalibration(collectionCalibrated.OCprofile(notOutlier), collectionCalibrated.positionRefined(notOutlier), plotSubResult);
        end
    
        % recalculate iOC based on calibration
        for i = 1:length(collection.iOC)
        
            Aint = interp1(calibration.x, calibration.A, collection.positionRefined{i});
            Y = collection.iOCprofile{i}./Aint;
            [collectionCalibrated.STDiOC(i), collectionCalibrated.iOC(i), selected] = std_modified(Y,1,1);
            collectionCalibrated.N(i) = sum(selected);
        
        end
    
    end

end

%% create collectionFiltered from collectionCalibrated and notOutliers
fnames = fieldnames(collectionCalibrated);
for i = 1:length(fnames)
    if length(collectionCalibrated.(fnames{i})) == length(notOutlier)
        collectionFiltered.(fnames{i}) = collectionCalibrated.(fnames{i})(:,notOutlier);
    else
        collectionFiltered.(fnames{i}) = collectionCalibrated.(fnames{i});
    end
end

collectionCalibrated.threshold= threshold; 
collectionCalibrated.calibration = calibration;

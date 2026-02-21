function makeFolderIfNotExisting(folderPath)

% mh, v1.0, 2026_02_19

    if ~exist(folderPath, 'dir')
        mkdir(folderPath);
    end

end
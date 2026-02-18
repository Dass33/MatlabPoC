function fileNames = getFileNamesInFolder(folderPath, options)

    arguments
        folderPath
        options.extension = '*.tiff'
    end

    files = dir( [folderPath, filesep, options.extension] );

    % fileNames = {files.name};
    fileNames = getFileName({files.name});

end
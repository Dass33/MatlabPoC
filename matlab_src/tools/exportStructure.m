function exportStructure(S, options)

    arguments
        S
        options.exportPath = '01.json'
    end


    if ~exist(fileparts(options.exportPath), 'dir')
        mkdir(fileparts(options.exportPath));
    end

    writestruct(S, options.exportPath, FileType='json')
    % writelines( jsonencode(S, PrettyPrint=true), options.exportPath);

end


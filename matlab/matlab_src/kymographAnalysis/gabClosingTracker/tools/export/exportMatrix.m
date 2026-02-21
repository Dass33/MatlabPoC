function exportMatrix(I, options)

    arguments
        I
        options.exportPath = '01.mat'
    end


    if ~exist(fileparts(options.exportPath), 'dir') & ...
            ~isempty(fileparts(options.exportPath))
        mkdir(fileparts(options.exportPath));
    end

    variableName = inputname(1);

    eval([variableName,' = I;']);

    save( options.exportPath, variableName );

end


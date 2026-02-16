function exportTable(T, options)

    arguments
        T
        options.exportPath = '01.csv'
    end


    if ~exist(fileparts(options.exportPath), 'dir')
        mkdir(fileparts(options.exportPath));
    end

    writetable(T, options.exportPath);

end


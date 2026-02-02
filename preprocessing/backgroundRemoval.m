function X = backgroundRemoval(D, B, options)

    arguments
        D
        B
        options.method = 'subtract'
    end

    switch options.method

        case 'subtract'
            X = D - B;

        case 'subtract_divide'
            X = (D - B)./B;

    end       
    
end
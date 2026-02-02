function X = preprocessing(R, options)

    arguments
        R
        options.Kt = 101
        options.defluctuationMethod = 'mean'
        options.bacgroundEstimationMethod = 'padded_movmean'
        options.backgroundRemovalMethod = 'subtract'
        options.whiteningMethod = 'std_division'
    end

    D = defluctuation(R, method=options.defluctuationMethod);

    B = backgroundEstimation(D, Kt=options.Kt, method=options.bacgroundEstimationMethod);

    X_tilde = backgroundRemoval(D, B, method=options.backgroundRemovalMethod);

    X = whitening(X_tilde, method=options.whiteningMethod);

end
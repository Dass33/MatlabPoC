function thresholded = thresholding(Y, noise_std, pfa)

    tau = significantThreshold(noise_std, pfa);
    thresholded = Y < tau;

end
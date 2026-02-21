function tau_neg = negativePeakThreshold(noise_std, noise_mean, pfa)

    tau_neg = noise_std * cdf_inv( pfa ) + noise_mean;

end
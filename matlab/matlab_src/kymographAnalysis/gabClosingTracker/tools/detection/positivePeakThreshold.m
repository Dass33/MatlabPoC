function tau_pos = positivePeakThreshold(noise_std, noise_mean, pfa)

    tau_pos = noise_std * Qinv( pfa ) + noise_mean;

end
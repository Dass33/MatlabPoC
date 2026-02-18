function tau = significantThreshold(noise_std, pfa)

    tau = noise_std * cdf_inv( pfa );

end
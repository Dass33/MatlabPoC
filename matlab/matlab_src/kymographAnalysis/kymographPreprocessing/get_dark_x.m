function d_x = get_dark_x(TemperatureMean, Calibration)

% Estimate time-invariant dak profile (d_x) from dark signal calibration using camera temperature (TemperatureMean) (interpolate or extrapolate across calibrations)
% Input: 
% - TemperatureMean: mean camera temperature recorded during acquisition
% - Calibration: struct with fields:
%    Calibration.TemperatureMean: 1 x M vector of calibration temperatures
%    Calibration.TemperatureMean: M x Nx matrix of dark profiles (d_x for each calibr temp)

% Output: d_x: Interpolated (or extrapolated darks ingla specific for camera
% temperature (TemperatureMean)

Nx = size(Calibration.DarkSignal,2);

if TemperatureMean < Calibration.TemperatureMean(1) || TemperatureMean > Calibration.TemperatureMean(end)
    disp('Temperature Calibration is missing!'); 

    %% extrapolation
    %dependency of total DarkSignal on temperature
    pf = polyfit(Calibration.TemperatureMean', mean(Calibration.DarkSignal,2),1);
    % mean profile * extrapolated mean value 
    d_x = mean(Calibration.DarkSignal./mean(Calibration.DarkSignal,2),1).*polyval(pf, TemperatureMean);

else

    %% interpolation
    d_x = interp2(1:Nx, Calibration.TemperatureMean, Calibration.DarkSignal, 1:Nx, TemperatureMean,'spline');
end
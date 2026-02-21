function data = simulateBackground(setting)

% setting.Nx = 464;
% setting.Nt = 2000;
% 
% setting.darkSignal.experimental = '/Volumes/data/Measurements/Dark signal calibration/2025-09-23-32pixels/2025_09_23-18_54_22/2025_09_23-18_54_22.tiff';
% 
% setting.beamProfile.width = 200;
% setting.beamProfile.maxIntensity = 80;
% setting.shotNoise = 1.5e-4;
% setting.beamProfile.intensityFluctuationSTD = 1e-3;
% setting.beamProfile.positionFluctuationD = 1e-2; %[pixel^2/frame]

Nx = setting.number_pixels;
Nt = setting.number_frames;

if isfield(setting, 'darkSignal')
    if strcmp(setting.darkSignal.type,'experimental')
        %dark = imread(setting.darkSignal.experimental);
        data = loadRawData(setting.darkSignal.file, 'tiff2');
        dark = data.Im;
    end
else 
    dark = 0;
    data.Dx = setting.Dt;
    data.Dt = setting.Dx;
end

if isfield(setting, 'beamProfile')

    if isfield(setting.beamProfile, 'positionFluctuationD') 
        dx0 = setting.beamProfile.positionFluctuationD*randn(Nt-1,1);
        x0 = cumsum([0;dx0]);
        x0 = x0-mean(x0);
    else 
        x0 = zeros(Nt,1);
    end

    x = 1:464; x = x-mean(x);
    c = setting.beamProfile.width/(2*sqrt(2*log(2)));
    light = setting.beamProfile.maxIntensity*exp(-0.5*(((x-x0)/c).^2));

    if isfield(setting.beamProfile, 'intensityFluctuationSTD') 

        intensityFluctuation = setting.beamProfile.intensityFluctuationSTD*randn(Nt,1);
        light = light.*(1 + intensityFluctuation);

    end

else

    light = ones(Nt,Nx);

end

if isfield(setting, 'shotNoise')

    shotNoise = setting.shotNoise.*sqrt(light*setting.beamProfile.maxIntensity).*randn(Nt,Nx);

else 

    shotNoise = 0;

end

I = light + shotNoise + dark;

%collect results
data.Im = I;
data.light = light;
data.dark = dark;

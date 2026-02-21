function HR = diffusivityToSize (Deff, channel_area)

%Stokes-Einstein equation corrected for hindrance effects associated with
%the diffusion of small objects in a restricted volume (equation 2 in the manuscript)
% according to Panadda Dechadilok and William M. Deen: Hindrance Factors for Diffusion and Convection in Pores

%the script solves the equation by Newton-Raphson method

%Deff - effective diffusivity [mum^2/s] - diffusivity of a particle inside a channel
%channel area [mum^2/s]
%HR - hydrodynamic radius [mum]

HR = ones(size(Deff));
kB=1.38064852*1e-23;	%[J?K?1]= [ kg?m2?s?2?K?1]
T=273.15 + 25 ;%absolute temperature [K]
ny=  8.9*1e-4 ;%viscosity [Pa?s] [(N?s)/m2 = kg/(s?m)]

for i = 1:length(Deff) 

    if not(isnan(Deff(i))) 
        
        %for i=1:length(Deff)
            HR0 = kB*T./(6*pi*ny*Deff(i)*1e-6) *1e12;
            f0 = hindranceFactor(HR0./sqrt(channel_area/pi)) * kB*T./(6*pi*ny*Deff(i)*1e-6) *1e12 - HR0;
            HR1 = HR0*0.9;
            f1 = hindranceFactor(HR1./sqrt(channel_area/pi)) * kB*T./(6*pi*ny*Deff(i)*1e-6) *1e12 - HR1;
            HR2 = HR0;
            
        %     close all
        %     plot(HR0, f0,'.'); hold on
        %     plot(HR1, f1,'.'); hold on
            while abs(HR0./HR1 - 1) > 0.0001
                HR2 = real(HR1 - (HR1-HR0)/(f1-f0)*f1);
                
                if imag(HR2)~=0
                    disp('')
                end
                f2 = real(hindranceFactor(HR2./sqrt(channel_area/pi)) * kB*T./(6*pi*ny*Deff(i)*1e-6) *1e12 - HR2);
                HR0=HR1;
                HR1=HR2;
                f0=f1;
                f1=f2;
        %         plot(HR2, f2,'.'); hold on
            end
            HR(i)=HR2;     
        %end
    
    else
    
        HR(i) = NaN;
    end
end

% for i=1:length(Deff)
%     K0 = 1;
%     K = Inf;
%     while abs(K/K0 - 1) > 0.01
%         K = K0;
%         HR(i) = K * kB*T./(6*pi*ny*Deff(i)*1e-6) *1e12;
%         lambda = HR(i)./sqrt(channel_area);
%         K0 = hindranceFactor(lambda);
%     end
% end

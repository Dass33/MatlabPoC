function [weight,calibration] = iOCToWeight (iOC, A, A_i, I_rel, material)

%iOC  - integrated optical contrast [um]
%weight - molecular weight [Da]
%calibration = weight/iOC [Da/um]


%A - area of a nanochannel [um2]
%A_i - are of the nanochannel without the coating [um2]
%I_rel - difference between the scattering intensity before and after the deposition - I_without/I_with

%material - default: protein; other option: lipids

n_i=1.33; %RI of the inside of a nanochannel
n_o=1.46; %RI of the outside of a nanochannel

if A == A_i %channel withut a coating

n_TE = 2*n_i^2/(n_i^2 - n_o^2);
n_TM = (n_i^2 + n_o^2)/(n_i^2 - n_o^2);
n_mean = 0.5*(n_TE + n_TM);

else

    f=A_i/A;
        
      n_s = sqrt((n_i^2-n_o^2)*(sqrt(1/I_rel)-f)/(1-f)+n_o^2); %for TE
      %n_s = %for TM
      
      n_mean=n_mean*sqrt(I_rel);
    
end

if strcmp(material,'protein')==1
        alpha_MW = 0.461e-12; %[mum2/Da]
elseif strcmp(material,'lipid')==1
        alpha_MW = 0.461e-12/1.85*1.6; %[mum2/Da]
else
    disp('iOCToWeight: define material of a particle!')
    return
end
        
calibration = A/alpha_MW/n_mean;
weight = iOC*calibration;

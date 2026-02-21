function C = kymographPreprocessing(data, setting)

%% remove dark background
if isnumeric(setting.darkCalibration) 
    d_x = setting.darkCalibration;
else 
    load(setting.darkCalibration)
    d_x = get_dark_x((data.TemperatureStart + data.TemperatureEnd)/2, Calibration);
end

I0 = data.Im - d_x;

%% denoise 
I = movmean(I0,16,2);

%% remove background
C = ones([size(data.Im), length(setting.Wx)]);

for iSweep = 1:length(setting.Wx)

    Wx = setting.Wx(iSweep);
    Wt = setting.Wt(iSweep);

    C(:,:,iSweep) = removeBackground(I, Wt, Wx);

end


% NSweep = length(setting.Wx);
% [Nt, Nx] = size(I);
% C = ones(Nt, Nx, NSweep);
% 
% 
% for iSweep = 1:length(setting.Wx)
% 
%     Wx = setting.Wx(iSweep);
%     Wt = setting.Wt(iSweep);
% 
%     for it = 1:Nt
% 
%         if it-Wt < 1
%             ind = it:it+Wt;
%         elseif it+Wt > Nt
%             ind = Nt-Wt:Nt;
%         else
%             ind = it-Wt:it+Wt;
%         end
% 
%         C0 = I(it,:)./I(ind,:);
%         C0 = C0./movmean(C0,2*Wx+1,2);
%         C(it,:, iSweep) = median(C0,1) -1;
% 
%     end
% end

% Wt = 10;
% Wx = 16;
% 
% epsilon_x = ones(size(I));
% epsilon_t = movmean(I./epsilon_x, Wt, 1);
% 
% for i = 1:25
%     epsilon_x = movmean(I./epsilon_t, Wx + i,2);
%     epsilon_t = movmean(I./epsilon_x, Wt +i, 1);
% end


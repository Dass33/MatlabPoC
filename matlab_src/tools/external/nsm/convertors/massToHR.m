function HR = massToHR (mass,type)

if strcmp(type,'globular')==1
    HR = 0.8846*(mass/1e3).^0.3265 * 1e-3;
elseif strcmp(type,'unfolded')==1
    HR = 0.7832*(mass/1e3).^0.5693 * 1e-3;
else HR = repmat(NaN,size(mass)); disp('massToHR: not defined type');
end


%https://www.fluidic.com/support/faq/convert-hydrodynamic-radius-to-mw/
%globular
% x=[10, 20, 50, 100, 200, 500, 1000,2000];
% y = [1.88, 2.36, 3.18, 3.98, 4.99, 6.72, 8.42,10.6];
% 
% plot(x,y,'.'); hold on
% x0=linspace(x(1),x(end),100);
% y0=0.8846*x0.^0.3265;
% plot(x0,y0)

% x=[10, 20, 50, 100, 200, 500, 1000,2000];
% y = [2.9,4.3,7.25,10.8,16,26.9,40,59.3];
% plot(x,y,'.'); hold on
% x0=linspace(x(1),x(end),100);
% y0=0.7832*x0.^0.5693;
% plot(x0,y0)

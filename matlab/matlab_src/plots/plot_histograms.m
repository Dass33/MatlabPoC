function plot_histograms(iOC, D, n)

%% iOC histogram
[N, edges] = weighted_histcounts (iOC*1e3,n,100);
figure;
bar(edges,N);
xlabel('iOC (nm)')
ylabel('Counts')

%% Deff histogram
[N, edges] = weighted_histcounts (D,n,200);
figure;
bar(edges,N);
xlabel('Diffusivity (\mum^2/s)')
ylabel('Counts')

%% iOC x Deff histogram
[N, edgesY, edgesX] = weighted_histcounts2 (D,iOC,n,50);
figure;
surf(edgesX,edgesY,N); view(2); shading flat; hold on
xlabel('iOC (nm)')
ylabel('Diffusivity (\mum^2/s)')
xlim([edgesX(1) edgesX(end)])
ylim([edgesY(1) edgesY(end)])

% %% definition of peaks
% number_of_peaks = input('Number_of_peaks?');
% for i=1:number_of_peaks
%     peak_iOCxDeff(i) = find_peak_from_2D_histogram(N, edgesY, edgesX);
% end
% 
% peak.iOC_mean = peak_iOCxDeff.X_mean;
% peak.iOC_FWHM = peak_iOCxDeff.X_FWHM;
% peak.Deff_mean = peak_iOCxDeff.Y_mean;
% peak.Deff_FWHM = peak_iOCxDeff.Y_FWHM;
% 
% %% MW x HR histogram
% %[N, edgesX, edgesY] = weighted_histcounts2 (HR,MW,n,300);
% 
% [N, edgesY, edgesX] = weighted_histcounts2 (HR,MW,n,HR_edges,MW_edges);
% HR_globular = massToHR (edgesX*1e3,'globular')*1000;
% figure;
% surf(edgesX,edgesY,N); view(2); shading flat; hold on
% plot3(edgesX,HR_globular,repmat(max(max(N))*2,size(edgesX)),'Color','white')
% xlabel('Molecular weight (kDa)')
% ylabel('Hydrodynamic radius (nm)')
% xlim([edgesX(1) edgesX(end)])
% ylim([edgesY(1) edgesY(end)])
% 
% %% definition of peaks
% number_of_peaks = input('Number_of_peaks?');
% for i=1:number_of_peaks
%     peak_MWxHR(i) = find_peak_from_2D_histogram(N, edgesY, edgesX);
% end
% 
% 
% %% add MW x HR peaks
% if exist('peak_MWxHR')==1
%     for i=1:length(peak_MWxHR)
%         theta = linspace(0,2*pi);
%         x=peak_MWxHR(i).X_mean + cos(theta)*3*peak_MWxHR(i).X_std;
%         y=peak_MWxHR(i).Y_mean + sin(theta)*3*peak_MWxHR(i).Y_std;
%         plot3(x,y,repmat(max(max(N))*2,size(x)),'Color',BasicColor(i));
%         text(peak_MWxHR(i).X_mean,peak_MWxHR(i).Y_mean,...
%             strcat('[',num2str(peak_MWxHR(i).X_mean),',',num2str(peak_MWxHR(i).Y_mean),']'),...
%             'Color',BasicColor(i));
%     end
% end
% 
% %% add iOC and D axis to MW and HR histogram
% ax1=gca;
% box off
% hold on
% 
% YTickLabel0=fliplr([0.1,0.2,0.5,1,2,5,10,20,50]);
% YTickLabel=[];
% for i=1:length(YTickLabel0)
%     YTickLabel{i}=YTickLabel0(i);
% end
% YTick = EffectiveDiffusivityToSize (YTickLabel0, nanochannelArea);
% 
% ax2=axes('Position', ax1.Position,'XAxisLocation', 'top','YAxisLocation','right','color','none',...
%     'YTick',YTick*1000,'YTickLabel',YTickLabel);
% line(-[ax1.XLim(1), ax1.XLim(2)]/calibration*1e6,[ax1.YLim(1), ax1.YLim(2)], 'Color','none')
% xlim(-[ax1.XLim(1), ax1.XLim(2)]/calibration*1e6)
% ylim([ax1.YLim(1), ax1.YLim(2)])
% xlabel('iOC (nm)')
% ylabel('Diffusivity (\mum^2/s)')
% 
% %% add D axis to MW and HR histogram
% ax1=gca;
% box off
% hold on
% 
% YTickLabel0=fliplr([0.1,0.2,0.5,1,2,5,10,20,50]);
% YTickLabel=[];
% for i=1:length(YTickLabel0)
%     YTickLabel{i}=YTickLabel0(i);
% end
% YTick = EffectiveDiffusivityToSize (YTickLabel0, nanochannelArea);
% 
% ax2=axes('Position', ax1.Position,'XAxisLocation', 'top','YAxisLocation','right','color','none',...
%     'YTick',YTick*1000,'YTickLabel',YTickLabel);
% line([ax1.XLim(1), ax1.XLim(2)],[ax1.YLim(1), ax1.YLim(2)], 'Color','none')
% xlim([ax1.XLim(1), ax1.XLim(2)])
% ylim([ax1.YLim(1), ax1.YLim(2)])
% %xlabel('iOC (nm)')
% ylabel('Diffusivity (\mum^2/s)')
% 
% 
% %% MW histogram
% %[N, edges] = weighted_histcounts (MW,n,1000);
% [N, edges] = weighted_histcounts (MW,n,MW_edges);
% figure;
% bar(edges,N,...
%     'FaceColor',[0.8 0.8 0.8],...
%     'EdgeColor','none'); hold on
% xlabel('Molecular weight (kDa)')
% ylabel('Counts')
% xlim([edges(1) edges(end)])
% 
% if exist('peak_MWxHR')==1
%     for i=1:number_of_peaks
%         a=MW>peak_MWxHR(i).X_mean-3*peak_MWxHR(i).X_std & MW<peak_MWxHR(i).X_mean+3*peak_MWxHR(i).X_std...
%             & HR>peak_MWxHR(i).Y_mean-3*peak_MWxHR(i).Y_std & HR<peak_MWxHR(i).Y_mean+3*peak_MWxHR(i).Y_std;
%         [N, edges] = weighted_histcounts (MW(a),n(a),MW_edges);
%         bar(edges,N,...
%             'FaceColor',BasicColor(i),...
%             'EdgeColor','none');
%         plot(edges,peak_MWxHR(i).X_N*exp(-0.5*((edges-peak_MWxHR(i).X_mean)/(peak_MWxHR(i).X_std)).^2),...
%           'Color',BasicColor(i)) 
%        text(peak_MWxHR(i).X_mean,peak_MWxHR(i).X_N,...
%            strcat(num2str(peak_MWxHR(i).X_mean)),...
%             'Color',BasicColor(i));
%     end
% end
% 
% %% add iOC axis to MW histogram
% ax1=gca;
% box off
% hold on
% 
% ax2=axes('Position', ax1.Position,'XAxisLocation', 'top','YAxisLocation','right','color','none',...
%     'YTick',[]);
% line(-[ax1.XLim(1), ax1.XLim(2)]/calibration*1e6,[ax1.YLim(1), ax1.YLim(2)], 'Color','none')
% xlim(-[ax1.XLim(1), ax1.XLim(2)]/calibration*1e6)
% ylim([ax1.YLim(1), ax1.YLim(2)])
% xlabel('iOC (nm)')
% 
% 
% 
% %% HR histogram
% %[N, edges] = weighted_histcounts (HR,n,1000);
% [N, edges] = weighted_histcounts (HR,n,HR_edges);
% figure;
% bar(edges,N,...
%     'FaceColor',[0.8 0.8 0.8],...
%     'EdgeColor','none'); hold on
% xlabel('Hydrodynamic radius (nm)')
% ylabel('Counts')
% xlim([0, edges(end)])
% 
% if exist('number_of_peaks')==1
%     for i=1:number_of_peaks
%         a=MW>peak_MWxHR(i).X_mean-3*peak_MWxHR(i).X_std & MW<peak_MWxHR(i).X_mean+3*peak_MWxHR(i).X_std...
%             & HR>peak_MWxHR(i).Y_mean-3*peak_MWxHR(i).Y_std & HR<peak_MWxHR(i).Y_mean+3*peak_MWxHR(i).Y_std;
%         [N, edges] = weighted_histcounts (HR(a),n(a),HR_edges);
%         bar(edges,N,...
%             'FaceColor',BasicColor(i),...
%             'EdgeColor','none');
%         plot(edges,peak_MWxHR(i).Y_N*exp(-0.5*((edges-peak_MWxHR(i).Y_mean)/(peak_MWxHR(i).Y_std)).^2),...
%           'Color',BasicColor(i)) 
%        text(peak_MWxHR(i).Y_mean,peak_MWxHR(i).Y_N,...
%            strcat(num2str(peak_MWxHR(i).Y_mean)),...
%             'Color',BasicColor(i));
%     end
% end
% 
% 
% %% add D axis on HR histogram
% box off
% hold on
% 
% XTickLabel0=fliplr([0.2,0.5,1,2,5,10,20,50]);
% XTickLabel=[];
% for i=1:length(XTickLabel0)
%     XTickLabel{i}=XTickLabel0(i);
% end
% XTick = EffectiveDiffusivityToSize (XTickLabel0, nanochannelArea);
% 
% ax1=gca;
% ax2=axes('Position', ax1.Position,'XAxisLocation', 'top','YAxisLocation','right','color','none',...
%     'XTick',XTick*1000,'XTickLabel',XTickLabel,'YTick',[]);
% line([0, edges(end)],[0 max(N)*1.2], 'Color','none')
% xlim([0, edges(end)])
% ylim([0 max(N)*1.2])
% xlabel('Diffusivity (\mum^2/s)')
% 
% %% scatter plot MW x R
% figure;
% plot(MW,HR,'.');
% xlabel('Molecular weight (kDa)')
% ylabel('Hydrodynamic radius (nm)')
% 
% 
% %% kernel-like histograms
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% 
% w0_iOC = 1e-4*sqrt(20)*20*29.5; %uncertainity in iOC for one frame
% w0_D = D*sqrt(6); %uncertainity in D for one frame
% 
% %% iOC histogram - kernel-like
% [N, edges] = kernel_like_histogram (iOC, n, 1000, w0_iOC);
% figure;
% bar(edges,N);
% xlabel('iOC (nm)')
% ylabel('Counts')
% 
% %% Deff histogram - kernel-like
% [N, edges] = kernel_like_histogram (D, n, 1000, w0_D);
% figure;
% bar(edges,N);
% xlabel('Diffusivity (\mum^2/s)')
% ylabel('Counts')
% 
% %% iOC x Deff histogram - kernel-like
% [N, edgesX, edgesY] = kernel_like_histogram2 (D,iOC,n,100, 1000, w0_D, w0_iOC);
% figure;
% surf(edgesY,edgesX,N); view(2); shading flat
% xlabel('iOC (nm)')
% ylabel('Diffusivity (\mum^2/s)')
% 
% 
% 
% 
% 
% 

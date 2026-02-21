function plotKymograph(I, Trajectory, Title)

% mh, v1.0, 2026_02_19

%% plot kymograph
figure('Units','normalized','OuterPosition',[0 0 1 0.5]);

%surf(1:size(I,1),1:size(I,2),I'); shading flat; view(2);  hold on; %colorbar;
imagesc(1:size(I,1),1:size(I,2),I');

colormap(bone)

ylim([1 size(I,2)])
xlim([1 size(I,1)])

ylabel('Pixel')
xlabel('Time frame')

%clim([1-3*std(I(:)) 1+3*std(I(:))])
clim([-3*std(I(:),'omitnan') 3*std(I(:),'omitnan')])
box off
hold on

if nargin == 3
    title(Title, Interpreter='none');
end

%% plot trajectory
if nargin > 1
    
    for itra=1:length(Trajectory.timeFrame)
        
         plot(Trajectory.timeFrame{itra},Trajectory.positionRefined{itra},...
             'Color',BasicColor(mod(itra,8)+1),'Marker','.')
         
         
         text(Trajectory.timeFrame{itra}(1),Trajectory.positionRefined{itra}(1),2,...
             {strcat('iOC=',num2str(-Trajectory.iOC(itra)*1e3)),strcat('D=',num2str(Trajectory.D(itra))), strcat('v=',num2str(Trajectory.velocity(itra)))},...
                 'Color',BasicColor(mod(itra,8)+1), 'FontSize',14);%,...
                 %'BackgroundColor',[1 1 1],'EdgeColor',[1 1 1])

    end

end

drawnow;


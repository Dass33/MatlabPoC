function scatterPlotCollection(collection, plotProperties, Marker, lineParams, notOutlier)

iProperties0 = length(plotProperties)-1;

labelX = plotProperties{1};
labelY = cell(1,0);
for i = 1:iProperties0
    for j = 1:size(collection.(plotProperties{i+1}),1)
        labelY{length(labelY)+1} = plotProperties{i+1};
    end
end

X = collection.(plotProperties{1});
Y = cell(iProperties0,1);
for i = 1:iProperties0
    Y{i} = collection.(plotProperties{i+1});
end
Y = cell2mat(Y);
iProperties = size(Y,1);

if nargin == 5 % if outliers are specified
    X = X(notOutlier);
    Y = Y(notOutlier);
end


% number of subplots in the figure
sizePlot1 = floor(sqrt(iProperties));
sizePlot2 = ceil((iProperties)/sizePlot1);

  
for i = 1:iProperties

    subplot(sizePlot1, sizePlot2, i)

    if strcmp(Marker,'Nweighted')

        W = collection.N/max(collection.N);
        for j = 1:length(X)
            scatter(X(j), Y(i,j), 'MarkerFaceAlpha',W(j),...
                'MarkerFaceColor','black',...
               'MarkerEdgeColor','none'); hold on
        end

    else

        plot(X, Y(i,:), Marker); hold on
    end
    xlabel(labelX)
    ylabel(labelY{i})

end

% plot circles defined by the center MEAN and radius 3*STD
if nargin > 3

 if isfield(lineParams, 'MEAN') && isfield(lineParams, 'STD')   

     %this needs to be modified for more than 1 in plotProperty, similar as
     %in the case for thresholds!

    for i = 1:length(plotProperties)-1
       if isfield(lineParams.MEAN, plotProperties{i+1}) && isfield(lineParams.MEAN, plotProperties{1}) 
        for j = 1:length(lineParams.MEAN.(plotProperties{i+1}))

            theta = linspace(0,2*pi);
            x0 = lineParams.MEAN.(plotProperties{1})(j);
            y0 = lineParams.MEAN.(plotProperties{i+1})(j);
            x = 3*lineParams.STD.(plotProperties{1})(j)*cos(theta) + x0;
            y = 3*lineParams.STD.(plotProperties{i+1})(j)*sin(theta) + y0;
    
            subplot(sizePlot1, sizePlot2, i)
            plot(x,y,'LineWidth',2, 'Color', BasicColor(mod(j,8)+1))

            plot(x0,y0,'.','MarkerSize', 5,  'Color',BasicColor(mod(j,8)+1))

            text(x0,y0, ...
                {strcat(plotProperties{1},'=',num2str(x0)), ...
                 strcat(plotProperties{i+1},'=',num2str(y0))},...
                 'Color',BasicColor(mod(j,8)+1), 'FontSize',10)

        end
       end

    end

 end

 % plot lower threshold
 if isfield(lineParams, 'lower') 

    lower = cell(iProperties0,1);
    for i = 1:iProperties0
        lower{i} = lineParams.lower.(plotProperties{i+1});
        if size(lower{i},2) ~= length(X)
            lower{i} = repmat(lower{i},1, length(X));
        end
    end
    lower = cell2mat(lower);

     for i = 1:iProperties
             subplot(sizePlot1, sizePlot2, i)
             plot(X, lower(i,:));
     end

 end

  % plot upper threshold
 if isfield(lineParams, 'upper') 

    upper = cell(iProperties0,1);
    for i = 1:iProperties0
        upper{i} = lineParams.upper.(plotProperties{i+1});
        if size(upper{i},2) ~= length(X)
            upper{i} = repmat(upper{i},1, length(X));
        end
    end
    upper = cell2mat(upper);

     for i = 1:iProperties
             subplot(sizePlot1, sizePlot2, i)
             plot(X, upper(i,:));
     end

 end

end
  
drawnow;
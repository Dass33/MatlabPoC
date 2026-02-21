function FIT = fit_gauss_robust(Y, MEAN_initial, FWHM_initial, plotResult)


if plotResult
    figure
end

% step in histogram
dx = FWHM_initial./logspace(3,0.5,10);

% number of subplots in the figure
sizePlot1 = floor(sqrt(length(dx)));
sizePlot2 = ceil((length(dx))/sizePlot1);

FIT.A = NaN(size(dx));
FIT.MEAN = NaN(size(dx));
FIT.STD = NaN(size(dx));

for i = 1:length(dx)

    edges = min(Y) - dx(i) : dx(i) : max(Y) + dx(i);
    N = histcounts(Y, edges);
    edges = (edges(2:end) + edges(1:end-1))/2;

    StartPoint(1) = interp1(edges,N,MEAN_initial);
    StartPoint(2) = MEAN_initial;
    StartPoint(3) = FWHM_initial/(2*sqrt(log(2)));

    fitresult = fit(edges', N', 'gauss1',...
        'StartPoint', StartPoint);

    
    FIT.A(i) = fitresult.a1;
    FIT.MEAN(i) = fitresult.b1;
    FIT.STD(i) = fitresult.c1/sqrt(2);
    
    if plotResult
        subplot(sizePlot1, sizePlot2, i)
        plot(fitresult,edges, N)
        title(strcat('dx=', num2str(dx(i))))
    end

end

FIT.FWHM = 2*sqrt(2*log(2))*FIT.STD;
FIT.RESOLUTION = -FIT.MEAN./FIT.FWHM; 
FIT.dx = dx;

if plotResult
    figure
    subplot(2,2,1)
    semilogx(dx, FIT.A)
    xlabel('dx')
    ylabel('A')
    
    subplot(2,2,2)
    semilogx(dx, FIT.MEAN)
    xlabel('dx')
    ylabel('MEAN')
    
    subplot(2,2,3)
    semilogx(dx, FIT.FWHM)
    xlabel('dx')
    ylabel('FWHM')
    
    subplot(2,2,4)
    semilogx(dx, FIT.RESOLUTION)
    xlabel('dx')
    ylabel('RESOLUTION')
end




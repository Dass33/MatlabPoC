function FIT = fit_gauss_distribution(Y, NFWHM, MEAN_initial, FWHM_initial, plotResult)


if plotResult
    figure
end

% step in histogram
dx = FWHM_initial./NFWHM;

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
    
    % if plotResult
    %     subplot(sizePlot1, sizePlot2, i)
    %     bar(edges, N); hold on
    %     edges_refine = linspace(edges(1), edges(end), length(edges)*20);
    %     plot(edges_refine, feval(fitresult, edges_refine))
    %     title(strcat('NFWHM=', num2str(NFWHM(i))))
    % end

end

FIT.FWHM = 2*sqrt(2*log(2))*FIT.STD;
FIT.RESOLUTION = abs(FIT.MEAN./FIT.FWHM); 
FIT.dx = dx;

if plotResult
    figure
    subplot(2,2,1)
    semilogx(NFWHM, FIT.A,'Marker','.')
    xlabel('NFWHM')
    ylabel('A')
    
    subplot(2,2,2)
    semilogx(NFWHM, FIT.MEAN,'Marker','.')
    xlabel('NFWHM')
    ylabel('MEAN')
    
    subplot(2,2,3)
    semilogx(NFWHM, FIT.FWHM,'Marker','.')
    xlabel('NFWHM')
    ylabel('FWHM')
    
    subplot(2,2,4)
    semilogx(NFWHM, FIT.RESOLUTION,'Marker','.')
    xlabel('NFWHM')
    ylabel('RESOLUTION')
end




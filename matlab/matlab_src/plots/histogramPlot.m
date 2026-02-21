function histogramPlot(X, edges, fixedValues)

N = histcounts(X, edges);
edges = (edges(1:end-1) + edges(2:end))/2;

Lower = [0, min(edges), 0];
Upper = [Inf, max(edges), Inf];

if nargin == 3
    for i = 1:3
        if not(isnan(fixedValues(i)))
            Lower(i) = fixedValues(i);
            Upper(i) = fixedValues(i);
        end
    end
end

fitresult = fit(edges', N', 'gauss1', ...
    'Lower', Lower,...
    'Upper', Upper);

figure
bar(edges, N); hold on
edges_refine = linspace(edges(1), edges(end), length(edges)*20);
plot(edges_refine, feval(fitresult, edges_refine))



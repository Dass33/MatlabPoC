function COST = dataSplitCost (x, ind)

%probability of a data set to be two different dat asets devided at ind-th
%element to two datasets = exp(-0.5*(((x-COST)/STD)^2)

STD = std(x,1);
N = length(x);

% expected STD of the difference between x(1:ind) and x(ind+1:end)
DIFFSTD = STD*sqrt(1./a + 1./(N-a));

% difference between x(1:ind) and x(ind+1:end)
DIFF = x(1:ind) - x(ind+1:end);

COST = abs(DIFF)/DIFFSTD;


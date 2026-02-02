function y = harmmean(x)

    y = numel(x) ./ sum(1 ./ x(:));

end

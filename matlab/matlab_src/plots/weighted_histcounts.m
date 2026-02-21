function [N, edges, bin] = weighted_histcounts (X,n,nbins)

% similar to function histcount - it partitions the X values into bins and
% returns the bin counts (N) and the bin edges (edges). Each X values is counted for in the bin n-times. 
% if nbins is a scalar, it specifies number of bins 
% if nbins is a vector, it specifies edges

if isempty(X) == 0

    if sum(n==1)==length(n)
        X2=X;
    else
        X2=[];
        for i = 1:length(X)
            X2 = [X2, repmat(X(i),1,n(i))];
        end
    end
    
    if length(nbins)==1
        
        [N, edges, bin] = histcounts (X2,nbins);
        
    else
        
        % Dedges = nbins(2) - nbins(1);
        % edges0=(nbins(1:end-1) + nbins(2:end))/2;
        % edges0=[edges0(1) - Dedges, edges0,edges0(end) +  Dedges];
        [N, edges0, bin] = histcounts (X2,nbins);
        
    end
    
    
    edges=(edges0(1:end-1) + edges0(2:end))/2;

else

    N = [];
    edges = [];

end

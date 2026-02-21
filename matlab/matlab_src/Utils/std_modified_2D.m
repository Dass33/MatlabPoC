function [MEANx, MEANy, STDx, STDy, Eta, selected] = std_modified_2D(x,y, diagonal)

selected = ~(isnan(x)) & ~isnan(y);
selected0 = ~(selected);

MEANx = NaN;
MEANy= NaN;
STDx = NaN;
STDy = NaN;
Eta = NaN;

if nargin < 3
    diagonal = false;
end

while sum(selected ~= selected0) > 0

    selected0 = selected;

    STDx = std(x(selected));
    MEANx = mean(x(selected));
    STDy = std(y(selected));
    MEANy = mean(y(selected));
    if diagonal
        COV = 0;
    else
        COV = sum((y(selected) - MEANy).*(x(selected) - MEANx))./(sum(selected) - 1);
    end
    Eta = [STDx.^2, COV; COV, STDy.^2];

    % A = [x' - MEANx; y' - MEANy];

    % P = ones(size(x));
    % for i = 1:length(x)
    %     P(i) = A(:,i)'*inv(Eta)*A(:,i);
    % end

    X = x - MEANx;
    Y = y - MEANy;
    a1 = Eta(1,1); a2 = Eta(1,2); a3 = Eta(2,1); a4 = Eta(2,2);
    P = (a4*X.^2 - (a2+a3)*X.*Y+ a1*Y.^2)./(a1*a4 - a2.*a3);

    selected = P < 9;

    % hold off
    % plot(x, y,'.'); hold on
    % plot(x(selected), y(selected),'o');

end
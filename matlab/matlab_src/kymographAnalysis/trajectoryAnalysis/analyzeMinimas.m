function [iOC, position, baseLength] = analyzeMinimas(I, sub1, sub2, threshold)

[Nt, Nx] = size(I);
N = length(sub1);
ind = sub2ind(size(I), sub1, sub2);

%% decide if peak or dip
ind_peaks = I(ind) >= 0;
I(sub1(ind_peaks),:) = - I(sub1(ind_peaks),:);

%% define maximum I until it will integrate
maxI = I(ind)*threshold;

iOC = NaN(N,1);
position = NaN(N,1);
baseLength = NaN(N,1);

for i = 1:N

    if I(ind(i)) <= 0

        % find boundaries
        bLeft = sub2(i);
        while bLeft > 1 && I(sub1(i), bLeft - 1) <= maxI(i)
             bLeft = bLeft - 1;
        end
        % bLeft = bLeft - 1;
        % %add first positive bump
        % while bLeft > 1 && I(sub1(i), bLeft - 1) >= maxI(i)
        %      bLeft = bLeft - 1;
        % end

    
        bRight = sub2(i);
        while bRight < Nx && I(sub1(i), bRight + 1) <= maxI(i)
             bRight = bRight + 1;
        end
        % bRight = bRight + 1;
        % %add first positive bump
        % while bRight < Nx && I(sub1(i), bRight + 1) >= maxI(i)
        %      bRight = bRight + 1;
        % end
    
        % calculate position of edges
        if bLeft == 1
            xLeft = 1;
        else
            dI1 = (I(sub1(i), bLeft - 1) - I(sub1(i), bLeft));
            if dI1 ~= 0
                dI2 =  maxI(i) - I(sub1(i), bLeft);
                xLeft = bLeft - dI2./dI1;
            else
                xLeft = bLeft;
            end
        end

        if bRight == Nx
            xRight = Nx;
        else
            dI1 = (I(sub1(i), bRight + 1) - I(sub1(i), bRight));
            if dI1 ~= 0
                dI2 = maxI(i) - I(sub1(i), bRight);
                xRight = bRight + dI2./dI1;
            else
                xRight = bRight;
            end
        end

        x = [xLeft, bLeft : bRight, xRight];
        y = [maxI(i), I(sub1(i), bLeft : bRight), maxI(i)];
    
        % hold off
        % plot(1:Nx, I(sub1(i),:)); hold on
        % plot(1:Nx, maxI(i)*ones(1, Nx))
        % plot(sub2(i), I(sub1(i),sub2(i)), 'o');
        % plot(x, y, '.')
    
        % integrate and calculate the centroid
        iOC(i) = trapz(x, y);
        position(i) = trapz(x, x.*y)/trapz(x, y);
        baseLength(i) = xRight - xLeft;

    end

end

iOC(ind_peaks) = -iOC(ind_peaks);
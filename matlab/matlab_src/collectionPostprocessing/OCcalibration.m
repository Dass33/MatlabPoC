function calibration = OCcalibration(OC, plotResult)

plotSubResults = false;
threshold = 1e-3;
dx = 1;

Ntrajectories = length(OC);

%% definition of positionStart and positionEnd 
positionStart = ones(1, Ntrajectories);
positionEnd = ones(1, Ntrajectories);
for i = 1:Ntrajectories
    positionStart(i) = min(position{i});
    positionEnd(i) = max(position{i});
end
positionStart = max(positionStart);
positionEnd = min(positionEnd);

%% collect all position
ind_i = cell(1, Ntrajectories);
a = 0;
for i = 1:Ntrajectories
    ind_i{i} = a+1 : a+length(position{i});
    a = a+length(position{i});
end

position = cell2mat(position');
x = positionStart+dx/2:positionEnd-dx/2;
ind_x = cell(size(x));
for i = 1:length(x)
    ind_x{i} = find(position >= x(i) - dx/2 & position <= x(i) + dx/2);
end

notOutlierFrame = true(size(position));
notOutlierFrame(position < x(1) | position > x(end)) = false;

%% collect all OC
OC = cell2mat(OC');
OCnorm = NaN(size(OC));

%% calculate meaniOC, iOCnorm- normalized by mean value of each order
for i = 1:Ntrajectories
    ind = ind_i{i}(notOutlierFrame(ind_i{i}));
    meanOC = mean(OC(ind,:),1,'omitnan');
    OCnorm(ind,:) = OC(ind,:)./meanOC;
end

[OCstd, OCmean, selected] = std_modified_ND(OCnorm(notOutlierFrame,:),1);
notOutlierFrame(notOutlierFrame) = selected;

%% first estimation of M
[~, OCorder] = max(OCmean./OCstd);
M = OC(:,OCorder);

for iter = 1:10

    %% calculate meaniOC, iOCnorm - normalized by M
    for i = 1:Ntrajectories
        ind = ind_i{i}(notOutlierFrame(ind_i{i}));
        meanM = mean(M(ind),1,'omitnan');
        OCnorm(ind,:) = OC(ind,:)./meanM;
    end
    
    %% optimal weights
    [z, w, ~] = optimalLinearCombinationND(OCnorm(notOutlierFrame,:));
    
    mean(z)/std(z)
    
    M = OC * w;

end


%% solve equation iOC(i,x) = meaniOC(i)*A(x);  
notOutlierFrame0 = not(notOutlierFrame);
Aint = ones(size(iOC));
A = 0;
A0 = Inf;
iter = 0;
iOCnorm = ones(size(iOC));

if plotSubResults
    figure;
end

while sum(notOutlierFrame0~=notOutlierFrame) > 0 || sum(abs(A0 - A) > threshold) > 0

    notOutlierFrame0 = notOutlierFrame;
    A0 = A;
    iter = iter + 1;
    
    %% calculate meaniOC, iOCnorm
    Y = iOC./Aint;
    for i = 1:Ntrajectories
        ind = ind_i{i}(notOutlierFrame(ind_i{i}));
        meaniOC= mean(Y(ind),1,'omitnan');
        iOCnorm(ind) = iOC(ind)./meaniOC;
    end

    %% remove outliers
    Y = iOCnorm./Aint;
    [STD, ~, selected] = std_modified(Y(notOutlierFrame),1,1);
    notOutlierFrame(notOutlierFrame) = selected;

    %%  calculate A
    Y = iOCnorm;
    A = ones(size(x));
    Astd = ones(size(x));
    AN = ones(size(x));
    for i = 1:length(x)

        ind = ind_x{i}(notOutlierFrame(ind_x{i}));
        A(i) = mean(Y(ind,:),'all');
        Astd(i) = std(Y(ind,:),1,'all');
        AN(i) = length(ind);
    
    end
    A = A/mean(A,'omitnan');
    Aint = interp1(x,A, position);

    if plotSubResults
        subplot(2,3,1)
        plot(1:NM,STD,'Marker','.'); hold on
        xlabel('Morder no')
        ylabel('STD Mnorm')
    
        subplot(2,3,2)
        hold off
        Y = iOCnorm./Aint;
        plot(position, Y,'.'); hold on
        plot(position(notOutlierFrame), Y(notOutlierFrame), 'o')
        xlabel('x')
        ylabel('iOCnorm/A for Morder=')

        subplot(2,3,4)
        plot(x,A); hold on
        xlabel('x')
        ylabel('A')
        
        subplot(2,3,5)
        plot(x,Astd); hold on
        xlabel('x')
        ylabel('Astd')
    
        subplot(2,3,6)
        plot(x,AN); hold on
        xlabel('x')
        ylabel('AN')
    end


end

disp(strcat('iOCcalibration:', num2str(iter),'iteration steps'))


calibration.x = x;
calibration.A = A;
calibration.Astd = Astd;
calibration.AN = AN;

 if plotResult

     figure
    
        subplot(2,3,2)
        hold off
        Y = iOCnorm./Aint;
        plot(position, Y,'.'); hold on
        plot(position(notOutlierFrame), Y(notOutlierFrame), 'o')
        xlabel('x')
        ylabel('iOCnorm/A for Morder=')

        subplot(2,3,4)
        plot(x,A); hold on
        xlabel('x')
        ylabel('A')
        
        subplot(2,3,5)
        plot(x,Astd); hold on
        xlabel('x')
        ylabel('Astd')
    
        subplot(2,3,6)
        plot(x,AN); hold on
        xlabel('x')
        ylabel('AN')
    end



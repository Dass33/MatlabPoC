function PARTICLES = linking(DIPS, DIPSCOMB, Image)

Tlength = size(DIPSCOMB.ind,1);

%% separate into clusters
DIPS.clusterNo = zeros(size(DIPS.I));
clusterNoLast = 0;

for i=1:length(DIPSCOMB.I)

    ind = DIPSCOMB.ind(:,i);
    ind(DIPS.isDUMMY(ind)) = []; %not relevant for DUMMY - they can be in multiple clusters
    clusterNo = DIPS.clusterNo(ind);
    clusterNo = unique(clusterNo);
    clusterNo(clusterNo == 0) =[];

    if isempty(clusterNo) == 1

        clusterNoLast = clusterNoLast + 1;
        DIPS.clusterNo(ind) = clusterNoLast;

    else

        DIPS.clusterNo(ind) = clusterNo(1);

        for j=2:length(clusterNo)

            DIPS.clusterNo(DIPS.clusterNo == clusterNo(j)) = clusterNo(1);

        end

    end

end

DIPSCOMB.clusterNo = DIPS.clusterNo(DIPSCOMB.ind(1,:));
a = DIPSCOMB.clusterNo == 0;
i = 1;
while sum(a) > 0 
    i = i +1;
    DIPSCOMB.clusterNo(a) = DIPS.clusterNo(DIPSCOMB.ind(i,a));
    a = DIPSCOMB.clusterNo == 0;
end

% close all
% imagesc(Image); hold on
% for i = 1:clusterNoLast
%     a = DIPS.clusterNo == i;
%     plot(DIPS.position(a), DIPS.timeFrame(a),'.');
% end

%% linking for each cluster separately
CONforward = zeros(size(DIPS.timeFrame));
CONbackward = zeros(size(DIPS.timeFrame));
indT = 0;
TRAJECTORYnumber = zeros(size(DIPS.timeFrame));

for ic = 1:clusterNoLast

    a = DIPSCOMB.clusterNo == ic;

    if sum(a) > 0

        ind = DIPSCOMB.ind(:,a);

        % % filter only those that have potential to connect from the found
        % % minimal and maximal position
        % position = DIPS.position(ind);
        % minPosition = min(position(:));
        % maxPosition = max(position(:));
        % 
        % attachedToEnds = DIPS.position == minPosition | DIPS.position == maxPosition | DIPS.timeFrame == 1 | DIPS.timeFrame == DIPS.sI(1);
        % 
        % DIPSCOMBfiltered0 = 0;
        % DIPSCOMBfiltered = true(1, size(ind,2));
        % 
        % while sum(DIPSCOMBfiltered0) ~= sum(DIPSCOMBfiltered)
        % 
        %     forwardConnection = ind(2:end, DIPSCOMBfiltered);
        %     backwardConnection = ind(1:end-1, DIPSCOMBfiltered);
        % 
        %     DIPSfiltered_forward = false(size(attachedToEnds));
        %     DIPSfiltered_forward(forwardConnection) = true;
        %     DIPSfiltered_backward = false(size(attachedToEnds));
        %     DIPSfiltered_backward(backwardConnection) = true;
        %     DIPSfiltered = (DIPSfiltered_forward & DIPSfiltered_backward) | attachedToEnds;
        % 
        %     DIPSCOMBfiltered0 = DIPSCOMBfiltered;
        %     DIPSCOMBfiltered = DIPSfiltered(ind);
        %     DIPSCOMBfiltered = sum(DIPSCOMBfiltered, 1) == Tlength;
        % 
        %     % close all
        %     % imagesc(Image); hold on
        %     % ylim([min(DIPS.timeFrame(ind(1,:))) - Tlength, max(DIPS.timeFrame(ind(1,:))) + Tlength])
        %     % plot(DIPS.position(ind(:,DIPSCOMBfiltered)), DIPS.timeFrame(ind(:,DIPSCOMBfiltered)), 'Marker','.', 'Color', 'white')
        % 
        % end
        % 
        % ind = ind(:,DIPSCOMBfiltered);
        % a(a) = DIPSCOMBfiltered;

        I = DIPSCOMB.I(a);
        Istd = DIPSCOMB.Istd(a);
        D = DIPSCOMB.D(a);
        N = DIPSCOMB.N(a);

        % calculate cost
        COST_I = I - min(I,[],2);
        COST_I = COST_I./max(COST_I,[],2);

        COST_Istd = Istd - min(Istd, [], 2);
        COST_Istd = COST_Istd./max(COST_Istd,[],2);

        COST_D = D - min(D, [], 2);
        COST_D = COST_D./max(COST_D,[],2);

        COST_N = N - min(N, [], 2);
        COST_N = COST_N./max(COST_N,[],2);

        COST = COST_I.^2 + COST_Istd.^2 + COST_D.^2 + COST_N.^2;

        %sort according to COST
        [~, a] = sort(COST);
        ind = ind(:,a);

        % %used for troubleshooting
        % close all
        % imagesc(Image); hold on
        % ylim([min(DIPS.timeFrame(ind(1,:)))-5, max(DIPS.timeFrame(ind(1,:))) + size(ind,1)+ 5])

        for j=1:size(ind,2)

                ind1 = ind(:,j);
                CONforward_ind1 = [ind1(1:end-1), ind1(2:end)];
                CONbackward_ind1 = [ind1(2:end), ind1(1:end-1)];

                %not assume connection of DUMMY
                isDUMMY = DIPS.isDUMMY(ind1);
                CONforward_ind1(isDUMMY(1:end-1),:) = [];
                CONbackward_ind1(isDUMMY(2:end),:) = [];
                ind1(isDUMMY) = [];

                %not yet defined connections
                c1 = TRAJECTORYnumber(ind1);
                c = find(c1~=0);

                added = 0;
    
                if isempty(c) == 1 %new trajectory
                    
                    indT = indT+1;
                    indT0 = indT;
    
                    CONforward(CONforward_ind1(:,1)) = CONforward_ind1(:,2);
                    CONbackward(CONbackward_ind1(:,1)) = CONbackward_ind1(:,2);
                    TRAJECTORYnumber(ind1) = indT0;

                    added = 1;
    
                else
    
                    a1 = CONforward(CONforward_ind1(:,1)); %saved
                    b1 = CONbackward(CONbackward_ind1(:,1));
        
                    a2 = CONforward_ind1(:,2); %potential
                    b2 = CONbackward_ind1(:,2);
                    
                    a = find(a1~=0);
                    b = find(b1~=0);
    
                    if sum(a1(a) == a2(a)) == length(a) && sum(b1(b) == b2(b)) == length(b) %add to trajectory
    
                            indT0 = unique(c1(c));
                            for k=2:length(indT0)
                                TRAJECTORYnumber(TRAJECTORYnumber == indT0(k)) = indT0(1);
                            end
                            indT0 = indT0(1);
    
                            CONforward(CONforward_ind1(:,1)) = CONforward_ind1(:,2);
                            CONbackward(CONbackward_ind1(:,1)) = CONbackward_ind1(:,2);
                            TRAJECTORYnumber(ind1) = indT0;

                            added = 1;
        
                    end
    
                end
    
                
                % if added == 1
                % 
                %     %used for troubleshooting
                %     plot(DIPS.position(ind1),DIPS.timeFrame(ind1),'Marker','.','Color','white'); hold on
                %     disp(DIPS.timeFrame(ind1(1)));
                %     disp('')
                % end

          end 
    end
end

%% construct PARTICLES
fnames = {'timeFrame', 'positionRefined','position'};
PARTICLES = [];

    iT = 0;
    for i=1:indT
        a = TRAJECTORYnumber == i;
        if sum(a) >= size(DIPSCOMB.ind,1)
            if isempty(PARTICLES) == 1
                PARTICLES = struct(fnames{1},[],fnames{2},[],fnames{3},[]);
            end
            iT = iT + 1;
            for j=1:length(fnames)
                PARTICLES(iT).(fnames{j}) = DIPS.(fnames{j})(a);
            end
        end
    end






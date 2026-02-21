% clear;
% addpath('/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/nsm-data-analysis/particleAnalysis')
% 
% ExperimentFolder='/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/simulated_tests/simulated_noise_plus_simulated_diffusing_molecules/';
% SimulationFolder='/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/simulated_tests/simulated_diffusing_molecules/';
% 
% ExperimentTimeStamp=findXfiles(ExperimentFolder,'_M.mat');
% %exclude  iOC0_D0
% a = []
% for itest=1:length(ExperimentTimeStamp)
%     if strcmp(ExperimentTimeStamp{itest}(1:7),'iOC0_D0') == 0
%         a=[a,itest];
%     end
% end
% ExperimentTimeStamp = ExperimentTimeStamp(a);
% 
% clear;
function JSC = Jaccard_similarity_coefficient(PARTICLES, simulated, denoise_setting, Nx, fun)

%fun = 'match_DIPS';
%fun = 'match_DIPSconnection';
%fun = 'match_trajectory';

% ExperimentTimeStamp = 'iOC0.0001_D10';
% load(strcat(ExperimentTimeStamp,'_D.mat'))
% load(strcat(ExperimentTimeStamp,'_M.mat'))

% simulationFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/synthetic_data/particleSignatures/10000x600_DLS8_Dt0.005Dx0.0295/diffusing_molecules/';
% %simulationFolder = '/Users/barboraspackova/Library/CloudStorage/OneDrive-FyzikálníústavAVČR,v.v.i/_project/_gitlab/data/synthetic_data/particleSignatures/10000x600_DLS8_Dt0.005Dx0.0295/flowing_molecules/';
% a = strfind(ExperimentTimeStamp{itest},'_');
% simulationName = ExperimentTimeStamp{itest}(a+1:end);
% simulationPath = strcat(simulationFolder,'/',simulationName,'.mat');
% load(simulationPath)

maxInaccuracy = denoise_setting.Wm;
omitEnds = (denoise_setting.Wm +1)/2;


if strcmp(fun, 'match_DIPS')

    %% groud true
    % change structure of simulated
    for i=1:length(simulated.trajectory)
        simulated.trajectory(i).position = simulated.trajectory(i).position';
        simulated.trajectory(i).timeFrame = simulated.trajectory(i).timeFrame';
        if denoise_setting.accumulation>1
            simulated.trajectory(i).position = reshape(simulated.trajectory(i).position(1:floor(length(simulated.trajectory(i).position)/denoise_setting.accumulation)*denoise_setting.accumulation),denoise_setting.accumulation,[]);
            simulated.trajectory(i).position = mean(simulated.trajectory(i).position ,1);
            simulated.trajectory(i).timeFrame = floor(simulated.trajectory(i).timeFrame(denoise_setting.accumulation:denoise_setting.accumulation:end)/denoise_setting.accumulation);
        end
    end
    
    positionGT = [simulated.trajectory.position];
    timeFrameGT = [simulated.trajectory.timeFrame];

    %filter out the edges
    %a = positionGT>=(denoise_setting.Wm +1)/2 & positionGT<=Nx - (denoise_setting.Wm +1)/2;
    a = positionGT>=omitEnds & positionGT<=Nx - omitEnds;
    positionGT = positionGT(a);
    timeFrameGT = timeFrameGT(a);


    %% found particles
 if length(PARTICLES) == 0 | (length(PARTICLES) == 1 & length(PARTICLES(1).timeFrame) == 0)

    JSC.minTlength = 0;
    JSC.TP = 0; %true positives
    JSC.FN = length(positionGT); %false negative
    JSC.FP = 0; %false positive
    JSC.JSC = 0;

 else

    Tlength = zeros(size(PARTICLES));
    for i=1:length(PARTICLES)
        Tlength(i) = length(PARTICLES(i).timeFrame);
    end

    JSC.minTlength = unique(Tlength);
    JSC.TP = zeros(size(JSC.minTlength)); %true positives
    JSC.FN = zeros(size(JSC.minTlength)); %false negative
    JSC.FP = zeros(size(JSC.minTlength)); %false positive
    JSC.JSC = zeros(size(JSC.minTlength));

    % change structure of PARTICLES
    for i=1:length(PARTICLES)
        PARTICLES(i).positionRefined = PARTICLES(i).positionRefined';
        PARTICLES(i).timeFrame = PARTICLES(i).timeFrame';
        PARTICLES(i).Tlength = repmat(Tlength(i), 1 , length(PARTICLES(i).timeFrame));
    end

    position = [PARTICLES.positionRefined];
    timeFrame = [PARTICLES.timeFrame];
    Tlength = [PARTICLES.Tlength];

    %filter out the edges
    a = position>=omitEnds & position<=Nx - omitEnds;
    position = position(a);
    timeFrame = timeFrame(a);
    Tlength = Tlength(a);


    %% definition of matched particles
    matchedGT_all = zeros(size(timeFrameGT));
    matched_all = zeros(size(timeFrame));
    for i=1:length(timeFrameGT)
                a = find(timeFrameGT(i) == timeFrame & matched_all == 0);
                b = abs(position(a)-positionGT(i));
                c = find(b <= maxInaccuracy);
                if isempty(c) == 1 % match notfound
                else
                    [d,e] = min(b(c));
                    matchedGT_all(i) = Tlength(a(c(e)));
                    matched_all(a(c(e))) = 1;
        
        %             disp([timeFrame(a(c(e))),timeFrameGT(i)])
        %             disp([position(a(c(e))),positionGT(i)])
                end
     end

    %% loop for different minTlength
    for iT = 1:length(JSC.minTlength)

        matchedGT = matchedGT_all;
        matchedGT(matchedGT<JSC.minTlength(iT)) = 0;
        matchedGT(matchedGT>=JSC.minTlength(iT)) = 1;

        matched = matched_all(Tlength >= JSC.minTlength(iT));
            
        
            %%
            JSC.TP(iT) = sum(matchedGT); %true positives
            JSC.FN(iT) = sum(matchedGT == 0); %false negative
            JSC.FP(iT) = sum(matched == 0); %false positive
            JSC.JSC(iT) = JSC.TP(iT)./(JSC.TP(iT) + JSC.FN(iT) + JSC.FP(iT));

%             JSC.TP = sum(matchedGT); %true positives
%             JSC.FN = sum(matchedGT == 0); %false negative
%             JSC.FP = sum(matched == 0); %false positive
%             JSC.JSC = JSC.TP./(JSC.TP + JSC.FN + JSC.FP);
        
%             close all
%             %imagesc(data.Im); hold on
%             plot(positionGT, timeFrameGT,'.','Color','blue'); hold on
%             plot(position,timeFrame,'o','Color','blue');
%             a = matchedGT == 1;
%             plot(positionGT(a), timeFrameGT(a),'.','Color','red');
%             a = matched == 1;
%             plot(position(a),timeFrame(a),'o','Color','red');

    end
 end

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

elseif strcmp(fun, 'match_DIPSconnection') == 1

  if length(simulated.trajectory) == 0

    positionGT = [];
    timeFrameGT = [];

  else

    %% groud true
    % change structure of simulated
    for i=1:length(simulated.trajectory)
        simulated.trajectory(i).position = [simulated.trajectory(i).position(1:end-1)'; simulated.trajectory(i).position(2:end)'];
        simulated.trajectory(i).timeFrame = simulated.trajectory(i).timeFrame(1:end-1)';
        if denoise_setting.accumulation>1
            disp('Jaccrad_similarit_coefficient: not defind for denoise_setting.accumulation>1'); return
%             simulated.trajectory(i).position = reshape(simulated.trajectory(i).position(1:floor(length(simulated.trajectory(i).position)/denoise_setting.accumulation)*denoise_setting.accumulation),denoise_setting.accumulation,[]);
%             simulated.trajectory(i).position = mean(simulated.trajectory(i).position ,1);
%             simulated.trajectory(i).timeFrame = floor(simulated.trajectory(i).timeFrame(denoise_setting.accumulation:denoise_setting.accumulation:end)/denoise_setting.accumulation);
        end
    end
    
    positionGT = [simulated.trajectory.position];
    timeFrameGT = [simulated.trajectory.timeFrame];

    %filter out the edges
    [~,b] = find(positionGT(1,:)>=omitEnds & positionGT(1,:)<=Nx - omitEnds & positionGT(2,:)>=omitEnds & positionGT(2,:)<=Nx - omitEnds);
    positionGT = positionGT(:,b);
    timeFrameGT = timeFrameGT(b);

  end


    %% found particles
 if length(PARTICLES) == 0 | (length(PARTICLES) == 1 & length(PARTICLES(1).timeFrame) == 0)

    JSC.minTlength = 0;
    JSC.TP = 0; %true positives
    JSC.FN = length(positionGT); %false negative
    JSC.FP = 0; %false positive
    JSC.JSC = 0;

 else

    Tlength = zeros(size(PARTICLES));
    for i=1:length(PARTICLES)
        Tlength(i) = length(PARTICLES(i).timeFrame);
    end

    JSC.minTlength = unique(Tlength);
    JSC.TP = zeros(size(JSC.minTlength)); %true positives
    JSC.FN = zeros(size(JSC.minTlength)); %false negative
    JSC.FP = zeros(size(JSC.minTlength)); %false positive
    JSC.JSC = zeros(size(JSC.minTlength));

    % change structure of PARTICLES
    for i=1:length(PARTICLES)
        PARTICLES(i).positionRefined = [PARTICLES(i).positionRefined(1:end-1)'; PARTICLES(i).positionRefined(2:end)'];
        PARTICLES(i).timeFrame = PARTICLES(i).timeFrame(1:end-1)';
        PARTICLES(i).Tlength = repmat(Tlength(i), 1 , length(PARTICLES(i).timeFrame));
    end

    position = [PARTICLES.positionRefined];
    timeFrame = [PARTICLES.timeFrame];
    Tlength = [PARTICLES.Tlength];

        %filter out the edges
    [~,b] = find(position(1,:)>=omitEnds & position(1,:)<=Nx - omitEnds & position(2,:)>=omitEnds & position(2,:)<=Nx - omitEnds);
    position = position(:,b);
    timeFrame = timeFrame(b);
    Tlength = Tlength(b);


    %% definition of matched particles
    matchedGT_all = zeros(size(timeFrameGT));
    matched_all = zeros(size(timeFrame));
    for i=1:length(timeFrameGT)
                a = find(timeFrameGT(i) == timeFrame & matched_all == 0);
                b = abs(position(:,a)-repmat(positionGT(:,i),1,length(a)));
                c = find(b(1,:) <= maxInaccuracy & b(2,:) <= maxInaccuracy);
                if isempty(c) == 1 % match notfound
                else
                    [d,e] = min(b(c));
                    matchedGT_all(i) = Tlength(a(c(e)));
                    matched_all(a(c(e))) = 1;
        
        %             disp([timeFrame(a(c(e))),timeFrameGT(i)])
        %             disp([position(a(c(e))),positionGT(i)])
                end
     end

    %% loop for different minTlength

    for iT = 1:length(JSC.minTlength)

        matchedGT = matchedGT_all;
        matchedGT(matchedGT<JSC.minTlength(iT)) = 0;
        matchedGT(matchedGT>=JSC.minTlength(iT)) = 1;

        matched = matched_all(Tlength >= JSC.minTlength(iT));
            
        
            %%
            JSC.TP(iT) = sum(matchedGT); %true positives
            JSC.FN(iT) = sum(matchedGT == 0); %false negative
            JSC.FP(iT) = sum(matched == 0); %false positive
            JSC.JSC(iT) = JSC.TP(iT)./(JSC.TP(iT) + JSC.FN(iT) + JSC.FP(iT));

%             JSC.TP = sum(matchedGT); %true positives
%             JSC.FN = sum(matchedGT == 0); %false negative
%             JSC.FP = sum(matched == 0); %false positive
%             JSC.JSC = JSC.TP./(JSC.TP + JSC.FN + JSC.FP);
        
%             close all
%             a =  Tlength >= JSC.minTlength(iT);
%             position0 = position(:,a);
%             timeFrame0 = timeFrame(a);
%             %imagesc(data.Im); hold on
% %             plot(positionGT(1,:), timeFrameGT,'.','Color','blue'); hold on
% %             plot(position(1,:),timeFrame,'o','Color','blue');
%             a = matchedGT == 1;
%             plot(positionGT(1,a), timeFrameGT(a),'.','Color','red'); hold on
%             a = matched == 1;
%             plot(position0(1,a),timeFrame0(a),'o','Color','red');
%             a = matchedGT == 0;
%             plot(positionGT(1,a), timeFrameGT(a),'.','Color','blue');
%             a = matched == 0;
%             plot(position0(1,a),timeFrame0(a),'o','Color','blue');
%             disp('')

    end
 end

%% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

elseif strcmp(fun, 'match_trajectory') == 1
    
end




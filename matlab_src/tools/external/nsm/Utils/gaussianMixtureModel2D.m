function model = gaussianMixtureModel2D(K, X, Y, initial)

TolLnp = 1e-10;
N = length(X);

%% gaussian mixture model, multiple dimension, https://brilliant.org/wiki/gaussian-mixture-model/ %https://towardsdatascience.com/gaussian-mixture-models-explained-6986aaf5a95
%                 K = 2;
%                 X = m1;
%                 Y = m2;
                

%                 %initiale values
%                 [sigmaX,muX] = std_modified(X,1,1);
%                 [sigmaY,muY] = std_modified(Y,1,1);
%                 edges0X = min(X):sigmaX/10:max(X);
%                 edgesX = (edges0X(1:end-1)+edges0X(2:end))/2;
%                 edges0Y = min(Y):sigmaY/10:max(Y);
%                 edgesY = (edges0Y(1:end-1)+edges0Y(2:end))/2;
%                 [counts, edges0X, edges0Y] = histcounts2(X, Y, edges0X, edges0Y);
%                 counts = movmean(movmean(counts,10,1),10,2);
%                 [ind,subX, subY] = findLocalExtreme(counts, [10,10], 'maxima');
% 
%                 
%                 if length(ind)<K
%                     subX = repmat(subX,1,K);
%                     subY = repmat(subY,1,K);
%                 end
%                 muX = [edgesX(subX)];
%                 muY = [edgesY(subY)];
%                 phi= counts(subX,subY);
%                 phi=phi/sum(phi);
%                 phi=reshape(phi,1,K);
%                 sigmaX = repmat(sigmaX,1,K);
%                 sigmaY = repmat(sigmaY,1,K);
%                 sigmaX2 = sigmaX.^2;
%                 sigmaY2 = sigmaY.^2;
%                 covXY = repmat(0,1,K);

                %initiale values
%                 [sigmaX,muX] = std_modified(X,1,1);
%                 [sigmaY,muY] = std_modified(Y,1,1);
%                 muX = [muX, muX-sigmaX];%, muX+sigmaX];
%                 muY = [muY, muY+sigmaY];%, muY+sigmaY];
%                 
%                 sigmaX = repmat(sigmaX,1,K);
%                 sigmaY = repmat(sigmaY,1,K);
%                 sigmaX2 = sigmaX.^2;
%                 sigmaY2 = sigmaY.^2;
%                 covXY = repmat(0.1918e-9,1,K);
%                 phi = repmat(1/K,1,K);
% 
%                 %only m1 negative
%                 Y(X>0)=[];
%                 X(X>0)=[];
%                 N = size(X,1);

%                 close all
%                 figure
%                 subplot(1,2,1)
%                 hold off
% %                  imagesc(edgesX,edgesY,counts'); hold on
%                   
%                 plot(m1,m2,'.'); hold on
%                 plot(muX,muY,'o','Color','red','MarkerSize',20)
%                  [distributionX, distributionY] = ellipseDefinedByCovariance(sigmaX2, sigmaY2, covXY, muX, muY);
%                  plot(distributionX, distributionY)
%                  xlabel('m1')
%                  ylabel('m2')
%                  caxis([0 100])

            muX = initial.muX;
            muY = initial.muY;
            sigmaX2 = initial.sigmaX2;
            sigmaY2 = initial.sigmaY2;
            covXY = initial.covXY;
            phi = initial.phi;

            lnp=zeros(1,10000); lnp(1)=0; lnp(2)=Inf;
            kk=2;
            while abs(lnp(kk-1)-lnp(kk))>TolLnp && kk<length(lnp) 
                kk=kk+1;

                Nu = zeros(N,K);
                for i=1:K
                    A = sigmaX2(i)*sigmaY2(i) - covXY(i)^2;
                    Nu(:,i) = exp(-0.5*((X-muX(i)).^2*sigmaY2(i) + (Y-muY(i)).^2*sigmaX2(i) - 2*X.*Y.*covXY(i))/A)/2/pi/sqrt(A);
                end
                gama = phi.*Nu;
                gama = gama./(sum(gama,2)+eps);
                sumGama = sum(gama,1);

                phi = sumGama/N;
                muX = sum(gama.*X,1)./sumGama;
                muY = sum(gama.*Y,1)./sumGama;
                sigmaX2 = sum(gama.*(X-muX).^2,1)./sumGama;
                sigmaY2 = sum(gama.*(Y-muY).^2,1)./sumGama;
                covXY = sum(gama.*(X-muX).*(Y-muY),1)./sumGama;

%                 %condition of all the peaks similar
%                 sigmaX2 = mean(sigmaX2);
%                 sigmaX2 = repmat(sigmaX2,1,K);
%                 sigmaY2 = mean(sigmaY2);
%                 sigmaY2 = repmat(sigmaY2,1,K);
%                 covXY = mean(covXY);
%                 covXY = repmat(covXY,1,K);

                %fixed parameters of the peaks
                sigmaX2=initial.sigmaX2;
                sigmaY2=initial.sigmaY2;
                covXY=initial.covXY;

                %likelihood
                lnp(kk) = sum(log(sumGama));
                

% %                 subplot(4,2,1)
% %                 plot(kk,phi(1),'.'); hold on
% %                 ylabel('phi')
% %                 subplot(4,2,2)
% %                 plot(kk,phi(2),'.'); hold on
% %                 ylabel('phi')
% %                 subplot(4,2,3)
% %                 plot(kk,mu(1),'.'); hold on
% %                 ylabel('mu')
% %                 subplot(4,2,4)
% %                 plot(kk,mu(2),'.'); hold on
% %                 ylabel('mu')
% %                 subplot(4,2,5)
% %                 plot(kk,sigma(1),'.'); hold on
% %                 ylabel('sigma')
% %                 subplot(4,2,6)
% %                 plot(kk,sigma(2),'.'); hold on
% %                 ylabel('sigma')
% %                 subplot(4,2,7)
% %                 plot(kk, sum(phi),'.'); hold on
% %                 subplot(4,2,8)
% %                 plot(kk,lnp,'.'); hold on
% 
%                subplot(1,2,1)
%                 hold off
%                  %plot(X,Y,'.'); hold on
%                  [a,b,c] = histcounts2_modified(X,Y,100); caxis([0 10])
%                  imagesc(b,c,a'); hold on
%                 plot(muX,muY,'o','Color','red','MarkerSize',20)
%                  [distributionX, distributionY] = ellipseDefinedByCovariance(sigmaX2, sigmaY2, covXY, muX, muY);
%                  plot(distributionX, distributionY)
%                  xlabel('m1')
%                  ylabel('m2')
%                  caxis([0 100])
% 
%                  subplot(1,2,2)
%                   plot(kk,lnp(kk),'.'); hold on

            end
            if kk==length(lnp)
                disp('gaussianMixtureModel: didnot converged');
            else
                lnp = lnp(1:kk);
            end

            model.muX = muX;
            model.muY = muY;
            model.sigmaX2 = sigmaX2;
            model.sigmaY2 = sigmaY2;
            model.covXY = covXY;
            model.phi = phi;
            

            %%
            figure
            subplot(1,2,1)
                %hold off
                 plot(X,Y,'.'); hold on
                plot(muX,muY,'o','Color','red','MarkerSize',20)
                 [distributionX, distributionY] = ellipseDefinedByCovariance(sigmaX2, sigmaY2, covXY, muX, muY);
                 plot(distributionX, distributionY)
                 %plot(m1(ind_groundTrue), m2(ind_groundTrue),'o')
                 xlabel('X')
                 ylabel('Y')
                 %caxis([0 100])

                 subplot(1,2,2)
                  plot(1:kk,lnp,'.'); hold on

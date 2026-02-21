function iOC = integrateOpticalContrast(I,timeFrame, position, denoise_setting, W)

%X11=-(DLSW-1)/2:(DLSW-1)/2;
X11 = -W : W;
N=length(timeFrame);
    
if N >= 3
    
    X0=repmat(1:size(I,2),N,1);
    Y0=repmat(timeFrame,1,size(X0,2));
    Z0=I(timeFrame,:);
    X1=repmat(X11,N,1);
    X1=X1+repmat(position,1,size(X1,2));
    Y1=repmat(timeFrame,1,size(X1,2));
    
    Z1=interp2(X0,Y0,Z0,X1,Y1,'spline');
    Z1m=median(Z1,1);

    if denoise_setting.convNum < Inf
    
        fitresult=fit(X11',Z1m','gauss1',...
                'Lower',[-Inf,0,sqrt(2)*denoise_setting.ws],...
                'Upper',[0,0,3*sqrt(2)*denoise_setting.ws],...
                'TolFun',1e-9);
        iOC=sqrt(pi)*fitresult.a1*fitresult.c1;

    else

        ft = fittype('pointSpreadFunction (x,a,b,c,Wx)','problem','Wx');
        fitresult = fit(X11', Z1m', ft,...
                'problem', denoise_setting.Wx,...
                'StartPoint',[min(Z1m), 0, sqrt(2)*denoise_setting.ws],...
                'TolFun', 1e-7);
        iOC=sqrt(pi)*fitresult.a*fitresult.c;

        % close all
        % plot(X11, Z1m,'.'); hold on
        % y_fit = pointSpreadFunction(X11',fitresult.a,fitresult.b,fitresult.c,fitresult.Wx);
        % plot(X11, y_fit)


    end

        



    % hold off
    % plot(X11,Z1); hold on
    % plot(fitresult, X11, Z1m);

    % iOC0 = NaN*ones(1,N);
    % for i=1:N
    %     fitresult=fit(X11',Z1(i,:)','gauss1',...
    %             'Lower',[-Inf,0,DLS],...
    %             'Upper',[0,0,3*DLS],...
    %             'TolFun',1e-9);
    %     iOC0(i)=sqrt(pi)*fitresult.a1*fitresult.c1;
    % end
    % iOC0= [];
    
else
        
    iOC=NaN;
    
end





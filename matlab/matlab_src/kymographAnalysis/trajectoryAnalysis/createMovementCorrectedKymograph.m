function [ImageCorr, ImageMean, ImageStd] = createMovementCorrectedKymograph(Image,timeFrame, position, DLSW)

X11=-(DLSW-1)/2:(DLSW-1)/2;
N=length(timeFrame);
    

   
    
    X0=repmat(1:size(Image,2),N,1);
    Y0=repmat(timeFrame,1,size(X0,2));
    Z0=Image(timeFrame,:);
    X1=repmat(X11,N,1);
    X1=X1+repmat(position,1,size(X1,2));
    Y1=repmat(timeFrame,1,size(X1,2));
    
    %Image2=interp2(X0,Y0,Z0,X1,Y1,'spline');
    ImageCorr=interp2(X0,Y0,Z0,X1,Y1);
    A = isnan(ImageCorr);
    a = sum(A,2) == 0;
    ImageCorr = ImageCorr(a,:);

    % ImageMean = zeros(1, size(ImageCorr,2));
    % ImageStd = zeros(1, size(ImageCorr,2));
    % for i = 1:size(ImageCorr,2)
    %     [ImageStd(i), ImageMean(i)] = std_modified(ImageCorr(:,i), 1, 1);
    % end

    N = size(ImageCorr,1);
    ImageMean = mean(ImageCorr,1);
    ImageStd = std(ImageCorr,1,1)/sqrt(N);

   

    disp('')
    
    

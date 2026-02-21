function [C] = removeBackground_tests(I, params, data, Mask)

% Related to the two-pass kymograph reconstruction (implements Sections 4 in the documentation)
% Specifically - estimation of particle contrast (C) and residual opticla
% profile drift (epsilon) from residual field (R)

% Input: 
% - R: Residual, Nt x Nx matrix
% - params: struct with algorithm parameters 
% - Mask: Nt x Nx matrix which elements are 'false' for pixels and frames that contain particle's image, and 'true' elsewhere.

% Output: result, result.C_filtr = final contrast map (Nt x Nx), and various intermediate fields
%  .C, .epsilon 

version = 'test13b';
threshold = params.iterationThreshold;

[Nt, Nx] = size(I);
Wx = params.Wx;
Wt = params.Wt;

% %% tests
% D_t_test = data.dark - d_x;
% D_t_test = D_t_test - mean(mean(D_t_test));
% d_t_test = zeros(Nt,16);
% for i = 1:16
%     d_t_test(:,i) = mean(D_t_test(:,i:16:end),2);
% end
% %D_t_test0 = d_t_test*a;

if strcmp(version, 'test17') 
    
    %Wx = 100;
    Wx = 2*params.Wx;
    Wt = 2*params.Wt + 1;

    I = I - mean(data.dark,1);
    
    I = movmean(I,16,2);

    %p = movmean(I,100,1,'omitnan');
    p = I(1:end-1,:);
    I = I(2:end,:);

   
    
        A1 = 1./p;
        A2 = movmean(A1,Wx,2);
        A = A1 - A2; 
        A = A(:,1:end-1);

        dI = I(:,1:end-1) - I(:,2:end);
        C1 = dI./p(:,1:end-1);
        C2 = movmean(C1,Wx,2);
        C = C1 - C2;
    
        B1 = I./p;
        B2 = movmean(B1,Wx,2);
        B = B1 - B2;
        B = B(:,1:end-1);
    
        d = ones(Nt-1,1);
        delta = ones(Nt-1,1);
        W = Mask(1:end-1,1:end-1) & Mask(2:end,1:end-1);
        W(:,1:Wx-2) = false;
        W(:,end-Wx/2-1:end) = false;
        for i = 1:Nt-1
            %s = [A(i,1+Wx/2:end-Wx/2-1)',C(i,1+Wx/2:end-Wx/2)'] \ B(i,1+Wx/2:end-Wx/2-1)';
            s = [A(i,W(i,:))',C(i,W(i,:))'] \ B(i,W(i,:))';
            
            d(i) = s(1);
            delta(i) = s(2);
        end
    
        C = (I(:,1:end-1) - d - delta.*dI)./p(:,1:end-1);
        Cm = movmean(C,Wx,2);
        C = C./Cm;
        C = cumprod([ones(1,Nx-1); C]);
        Cm = movsum(C.*Mask(:,1:end-1),Wt,1)./movsum(Mask(:,1:end-1),Wt,1);
        C = C./Cm;
        C = C - 1;

        disp('')

elseif strcmp(version, 'test16') %tohle nefunguje s Maskou, nevim proc

    I = I - mean(data.dark,1);
    I = movmean(I,16,2);
    %W = ones(size(I));

    I = I(:,9:end-8);
    dI = I(:,1:end-1) - I(:,2:end);
    Mask = Mask(:,9:end-8);
    Mask = double(Mask);

    C = ones(Nt, size(dI,2));

    Wt = 10;

    for i = 1+2*Wt:Nt-2*Wt

%this one is interesting, perhps it is worthed to explore more
        j = [i-2*Wt:i-Wt, i+1+Wt:i+2*Wt];
        % j = [i-Wt-10:i-11, i+11:i+Wt+10];
        W1 = [Mask(j,1:end-1)',Mask(j,1:end-1)',Mask(i,1:end-1)'];
        W2 = Mask(i,1:end-1)';
        s = (W1.*[I(j,1:end-1)', dI(j,:)', ones(size(dI,2),1)]) \ (W2.*I(i,1:end-1)');
        C(i+1,:) = (sum(s(1:length(j)).*I(j,1:end-1),1) + sum(s(length(j)+1:2*length(j)).*dI(j,:),1) + s(end))./I(i,1:end-1);
        % C(i+1,:) = (sum(s(1:length(j)).*I(j,2:end-1),1) + s(end))./I(i,2:end-1);
    end

    disp('')

elseif strcmp(version, 'test15') %this has down to 30 of iOC./STDiOC test file

    I = I - mean(data.dark,1);
    I = movmean(I,16,2);
    %W = ones(size(I));
    %Mask = Mask(:,9:end-8);
    Mask = Mask(:,31:end-30);
    Mask2 = Mask(1:end-1,:) & Mask(2:end,:);
    Mask = double(Mask);
    Mask2 = double(Mask2);
    

    %I = I(:,9:end-8);
    I = I(:,31:end-30);
    dI = I(:,1:end-1) - I(:,2:end);
    %ddI = dI(:,1:end-1) - dI(:,2:end);

    C = ones(Nt, size(dI,2));
    x = 1:size(dI,2);
    A = [ones(size(dI,2),1)];%, x', x'.^2, x'.^3];
    for i = 1:Nt-1
    %     s = [A.*I(i,1:end-2)', dI(i,1:end-1)', ddI(i,:)', ones(size(ddI,2),1)] \ I(i+1,1:end-2)';
    %     C(i+1,:) = I(i+1,1:end-2)./(sum(s(1:size(A,2)).*A'.*I(i,1:end-2),1) + s(end-2)*dI(i,1:end-1) + s(end-1)*ddI(i,:)+ s(end));
        s = (Mask2(i,1:end-1)'.*[A.*I(i,1:end-1)', dI(i,:)', ones(size(dI,2),1)]) \ (Mask2(i,1:end-1)'.*I(i+1,1:end-1)');
        C(i+1,:) = I(i+1,1:end-1)./(sum(s(1:size(A,2)).*A'.*I(i,1:end-1),1) + s(end-1)*dI(i,:) + s(end));
    
    end

    % Cm = movmean(C,Wx,1);
    % C = cumprod(C./Cm,1);
    C = cumprod(C,1);
    Cm = movsum(C.*Mask(:,1:end-1),Wt,1)./movsum(Mask(:,1:end-1),Wt,1);
    C = C./Cm - 1;
    C = [zeros(Nt,30), C, zeros(Nt,31)];

    disp('')

elseif strcmp(version, 'test13') %for range of Wx and Wt iOC.STDiOC goes down to 25 for test kymographs and 11 for dna origami

    I = I - mean(data.dark,1);
    I = movmean(I,16,2);
    
        dI = I(2:end,:)./I(1:end-1,:);
        dIm = movmean(dI,Wx,2);
        dI = dI./dIm;
        C = cumprod([ones(1,Nx); dI],1);
        Cm = movsum(C.*Mask,Wt,1)./movsum(Mask,Wt,1);
        C = C./Cm - 1;
    
    
        % %create Mask
        % C_std = STD_profile(C);
        % %Mask = C.*(1 - exp(-0.5*(C./C_std).^2));
        % Mask = C < -4*C_std;

        %plot(C(400,:)); hold on
    


    disp('')

elseif strcmp(version, 'test13b') %for range of Wx and Wt iOC.STDiOC goes down to 25 for test kymographs and 11 for dna origami

    I = I - mean(data.dark,1);
    I = movmean(I,16,2);
    
    
        % Im = movmean(I,2*params.Wx+1,2);
        % C = I./Im;

        dI = I(2:end,:)./I(1:end-1,:);
        dIm = movmean(dI,2*params.Wt+1,2);
        dI = dI./dIm;
        C1 = cumprod([ones(1,Nx); dI],1);
        C1m = movmean(C1,2*params.Wt+1,1);
        C2 = C1./C1m;

        C0 = Inf(size(C1));
        C_std = ones(1, Nx);

        tol = 1;
        while sum(abs(C2 - C0)./C_std > tol,'all') > 0

            W = ones(size(C1));
            W(not(Mask)) = C2(not(Mask));
            Ccorr = C1./W;
            Cm = movmean(Ccorr,2*params.Wt+1,1);
            C0 = C2;
            C2 = C1./Cm;
            C_std = STD_profile(C2-1);
            C2 = C2.*W;
            

        end


        
    


    disp('')    

elseif strcmp(version, 'test12') %%this has down to 30 of iOC./STDiOC test file & 10 of dna origami


    I = I - mean(data.dark,1);
    I = movmean(I,16,2);
    I = I(:,9:end-8);
    dI = I(:,1:end-1) - I(:,2:end);
    Mask = Mask(:,9:end-8);
    Mask(:,1:30) = false; %because of not well tracked ends of trajeectories
    Mask(:,end-30:end) = false;
    %ddI = dI(:,1:end-2) - dI(:,3:end);

    % I1 = movmean(I,16,2);
    % I2 = movmean(I,32,2);
    % I3 = movmean(I,48,2);
    % I1 = I1(:,25:end-24);
    % I2 = I2(:,25:end-24);
    % I3 = I3(:,25:end-24);
    % 
    % dI1 = I1(:,1:end-2) - I1(:,3:end);
    % dI2 = I2(:,1:end-2) - I2(:,3:end);
    % dI3 = I3(:,1:end-2) - I3(:,3:end);

    % I1 = movmean(I,32,2);
    % I1 = I1(:,17:end-16);
    % dI1 = I1(:,1:end-2) - I1(:,3:end);%diff(I,1,2);
    % 
    % I = I(:,17:end-16);
    % dI = dI(:,17:end-16);

  % WWt = 1:50;
  % for iWt = 1:length(WWt)

    C = ones(size(dI));
    %I(i+1,:) = I
    %Wt = WWt(iWt);
    %Wt = 20;
    %for i = 1+Wt+10:Nt-Wt-10
    for i = 1+Wt:Nt-Wt

        % s = [I1(i,17:end-16-1)', I2(i,17:end-16-1)', dI1(i,17:end-16)', dI2(i,17:end-16)', ones(Nx-1-32,1)] \ I(i+1, 17:end-16-1)';
        % C(i+1,:) = (s(1)*I1(i,1:end-1) + s(2)*I2(i,1:end-1) + s(3)*dI1(i,:) + s(4)*dI2(i,:) + s(5))./I(i+1,1:end-1);
       
        % s = [I(i,1:end-1)', dI(i,:)', ones(size(dI,2),1)] \ I(i+1,1:end-1)';
        % C(i+1,:) = (s(1)*I(i,1:end-1) + s(2)*dI(i,:) + s(3))./I(i+1,1:end-1);
        
        % s = [I(i,1:end-1)', dI(i,:)', dI1(i,:)', ones(size(dI,2),1)] \ I(i+1,1:end-1)';
        % C(i+1,:) = (s(1)*I(i,1:end-1) + s(2)*dI(i,:) + s(3)*dI1(i,:) + s(4))./I(i+1,1:end-1);

        % %this one is interesting, perhps it is worthed to explore more
        % j = [i-Wt:i-1, i+1:i+Wt];
        % % j = [i-Wt-10:i-11, i+11:i+Wt+10];
        % s = [I(j,2:end-1)', dI(j,:)', ones(size(dI,2),1)] \ I(i,2:end-1)';
        % C(i+1,:) = (sum(s(1:length(j)).*I(j,2:end-1),1) + sum(s(length(j)+1:2*length(j)).*dI(j,:),1) + s(end))./I(i,2:end-1);
        % % C(i+1,:) = (sum(s(1:length(j)).*I(j,2:end-1),1) + s(end))./I(i,2:end-1);

        j = [i-Wt:i-1, i+1:i+Wt];
        C2 = ones(length(j), size(dI,2));
        stdC2 = ones(length(j),1);
        %x = 1:size(dI,2);
        for k = 1:length(j)
            % s = [I1(j(k),2:end-1)', dI1(j(k),:)', ones(size(dI1,2),1)] \ I1(i,2:end-1)';
            % C2(k,:) = (s(1)*I1(j(k),2:end-1) + s(2)*dI1(j(k),:) + s(3))./I1(i,2:end-1);

            % s = [I1(j(k),2:end-1)', dI1(j(k),:)', dI2(j(k),:)', dI3(j(k),:)', ones(size(dI1,2),1)] \ I1(i,2:end-1)';
            % C2(k,:) = (s(1)*I1(j(k),2:end-1) + s(2)*dI1(j(k),:) + s(3)*dI2(j(k),:)+ s(4)*dI3(j(k),:)+ s(5))./I1(i,2:end-1);

            % s = [I(j(k),3:end-2)', dI(j(k),2:end-1)', ddI(j(k),:)', ones(size(ddI,2),1), x', x'.^2] \ I(i,3:end-2)';
            % C2(k,:) = (s(1)*I(j(k),3:end-2) + s(2)*dI(j(k),2:end-1) + s(3)*ddI(j(k),:)+ s(4)+s(5)*x + s(6)*x.^2)./I(i,3:end-2);
            W = Mask(j(k),1:end-1) & Mask(i,1:end-1); 
            % s = (W'.*[I(j(k),1:end-1)', dI(j(k),:)', ones(size(dI,2),1), x'.*I(j(k),1:end-1)', x'.^2.*I(j(k),1:end-1)']) \ (W'.*I(i,1:end-1)');
            % C2(k,:) = I(i,1:end-1)./(s(1)*I(j(k),1:end-1) + s(2)*dI(j(k),:) + s(3) + s(4).*x.*I(j(k),1:end-1)+ s(5).*x.^2.*I(j(k),1:end-1));
            s = (W'.*[I(j(k),1:end-1)', dI(j(k),:)', ones(size(dI,2),1)]) \ (W'.*I(i,1:end-1)');
            C2(k,:) = I(i,1:end-1)./(s(1)*I(j(k),1:end-1) + s(2)*dI(j(k),:) + s(3));
            %stdC2(k) = std(C2(k,W));
        end

        % [a,b] = sort(stdC2);
        % relevant = b(1:Wt/2);

        C(i,:) = sum(C2.*Mask(j,1:end-1),1)./sum(Mask(j,1:end-1),1);
        %C(i,:) = sum(C2(relevant,:).*Mask(j(relevant),1:end-1),1)./sum(Mask(j(relevant),1:end-1),1);
        % if i==1400
        %     disp('')
        % end

    end
% STD(iWt,:) = std(C(1000:2000,:),1,1);
% disp(iWt)
%   end

    % C = cumprod(C,1);
    % C = C./movmean(C,100,1);
    C = C-1;
    C = [zeros(Nt,8),C, zeros(Nt,9)];
disp('')


elseif strcmp(version, 'test11')

    Wx = 16;

    I = I - mean(data.dark,1);

    I = imgaussfilt(I,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);

    I_omitted = I;
    I_omitted(not(Mask)) = NaN;

    % I_cheat = data.light + data.dark - mean(data.dark,1);
    % I_cheat = imgaussfilt(I_cheat,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);

     %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
        a = zeros(16, Nx);
        for i = 1:16
            a(i,i:16:end) = 1;
        end
    
        A1 = a./permute(I_omitted(1:end-1,:), [3,2,1]);
        A2 = movmean(A1,Wx,2);
        A = A1 - A2; 
    
        B1 = I_omitted(2:end,:)./I_omitted(1:end-1,:);
        B2 = movmean(B1,Wx,2);
        B = B1 - B2;
    
        d_t = ones(16, Nt-1);
        for i = 1:Nt-1
            %relevant = 1+Wx/2:Nx-Wx/2;
            relevant = not(isnan(B(i,:))) & sum(isnan(A(:,:,i)),1) == size(A,1);
            relevant(1:Wx/2-1) = false;
            relevant(Nx - Wx/2+1:Nx) = false;
            d_t(:,i) = A(:,relevant,i)' \ B(i,relevant)';
            %d_t(:,i) = (W(i,1+Wx/2:end-Wx/2)'.*A(:,1+Wx/2:end-Wx/2,i)') \ (W(i,1+Wx/2:end-Wx/2)'.*B(i,1+Wx/2:end-Wx/2)');
      
        end
    
        C = (I(2:end,:) - d_t'*a)./I(1:end-1,:);
        %C_cheat = (I_cheat(2:end,:) - d_t'*a)./I_cheat(1:end-1,:); 
        Cm = C;
        Cm(not(Mask(1:end-1,:)) & not(Mask(2:end,:))) = NaN;
        Cm = movmean(Cm,Wx,2);
        Cm =  interpolateNaNs(Cm,2);
        C = C./Cm;
        C = cumprod([ones(1, Nx); C],1);
        Cm = C;
        Cm(not(Mask)) = NaN;
        Cm = movmean(Cm,200,1);
        Cm =  interpolateNaNs(Cm,1);
        C = C./Cm;
        C = C - 1;

        disp('')
    
elseif strcmp(version, 'test10') %this works but estimation under Mask needs to be done

    Wx = 16;

    I = I - mean(data.dark,1);
    

    I = imgaussfilt(I,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    % I_omitted = I;
    % I_omitted(not(Mask)) = NaN;

    % I_cheat = data.light + data.dark - mean(data.dark,1);
    % I_cheat = imgaussfilt(I_cheat,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    %p = movmean(I_cheat,100,1);
    %p = repmat(I_cheat(500,:),Nt,1);
    p = movmean(I,100,1,'omitnan');

    %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
        a = zeros(16, Nx);
        for i = 1:16
            a(i,i:16:end) = 1;
        end
    
        A1 = a./permute(p, [3,2,1]);
        A2 = movmean(A1,Wx,2);
        A = A1 - A2; 
    
        B1 = I./p;
        B2 = movmean(B1,Wx,2);
        B = B1 - B2;
    
        d_t = ones(16, Nt);
        for i = 1:Nt
            d_t(:,i) = A(:,1+Wx/2:end-Wx/2,i)' \ B(i,1+Wx/2:end-Wx/2)';
        end
    
        C = (I - d_t'*a)./p;
        % Cm = C;
        % Cm(not(Mask)) = NaN;
        Cm = movmean(C,Wx,2);
        %Cm = interpolateNaNs(Cm,2);

        % C_cheat = (I_cheat - d_t'*a)./p; 
        % C = C./movmean(C_cheat,Wx,2);
        C = C./Cm;
        %C = C./movmean(C,50,2);
        C = C - 1;

        disp('')


elseif strcmp(version, 'test9')

    fun = 'subtract dark';

    %I = data.

    I = imgaussfilt(I,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);

    I_blank = imgaussfilt(data.light + data.dark - mean(data.dark,1),[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    I_cheat = imgaussfilt(data.light,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    %p = repmat(mean(I_cheat,1), Nt, 1);
    %p = movmean(I_cheat,Wt,1);
    p = I_cheat;

    % cheating
    W = (data.Im - data.dark)./data.light;
    W = imgaussfilt(W,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    W = W - 1;
    I_std = STD_profile(W);
    W = exp(-0.5*(W./I_std).^2);
   

    if strcmp(fun, 'subtract dark')

        %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
        a = zeros(16, Nx);
        for i = 1:16
            a(i,i:16:end) = 1;
        end
    
        A1 = a./permute(p, [3,2,1]);
        A2 = movmean(A1,Wx,2);
        A = A1 - A2; 
    
        B1 = I_blank./p;
        B2 = movmean(B1,Wx,2);
        B = B1 - B2;
    
        d_t = ones(16, Nt);
        for i = 1:Nt
            d_t(:,i) = A(:,1+Wx/2:end-Wx/2,i)' \ B(i,1+Wx/2:end-Wx/2)';
            %d_t(:,i) = (W(i,1+Wx/2:end-Wx/2)'.*A(:,1+Wx/2:end-Wx/2,i)') \ (W(i,1+Wx/2:end-Wx/2)'.*B(i,1+Wx/2:end-Wx/2)');
      
        end
    
        R = (I - d_t'*a)./p;

    else

        R = I./p;
    end

    %Rm = movmean(R,Wx,2);
    Rm = movsum(R.*W, Wx, 2)./movsum(W, Wx, 2);
    C = R./Rm-1;


    %C = imgaussfilt(C,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);

    

    disp('')

       

elseif strcmp(version, 'test8')

    %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
    a = zeros(16, Nx);
    for i = 1:16
        a(i,i:16:end) = 1;
    end

    

    %I = I - d_x;
    I = I - mean(data.dark,1);
    I = imgaussfilt(I,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    % dI = I(:,2:end) - I(:,1:end-1);
    % I = I(:,1:end-1);
    % a = a(:,1:end-1);

 for iter = 1:10
    %solve equation Im(i+1,:) = b_t*Im(i,:) + delta*dIm(i,:) + d_t 
    %s = ones(3,Nt-1);
    d_t = zeros(Nt-1, 16);
    b_t = ones(Nt-1,1);
    D_t = zeros(Nt, 16);
    B_t = ones(Nt, 1);
    %delta = zeros(Nt-1, Nx - 1);
    for i = 1:Nt-1
        W = 1;%./I(i,:);
        %s = (W'.*[I(i,:)', dI(i,:)', a']) \ (W'.*I(i+1,:)');
        s = (W'.*[I(i,:)', a']) \ (W'.*I(i+1,:)');
        %delta(i,:) = s(2).*dI(i,:);
        d_t(i,:) = s(2:end)';
        b_t(i) = s(1);
        D_t(i+1,:) = b_t(i)*D_t(i,:) + d_t(i,:);% + delta(i,:);
        B_t(i+1) = b_t(i).*B_t(i);
        
        %Im(i+1:end,:) = Im(i+1:end,:) - s(3);
    end

    


    %d_test = data.dark - d_x;
    d_test = data.dark - mean(data.dark,1);
    d_test = imgaussfilt(d_test,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]);
    D_test = ones(Nt,16);
    for i = 1:16
        D_test(:,i) = mean(d_test(:,i:16:end),2);
    end

    %dC = (I(2:end,:) - d_t*a - delta)./b_t./I(1:end-1,:);
    dC = (I(2:end,:) - d_t*a)./b_t./I(1:end-1,:);
    R = movmean(dC,16,2);
    dC = dC./R;
    dC = [ones(1, Nx); dC];
    C = cumprod(dC);
    C = C./mean(C,1);

    %D_t = D_t - mean(D_t,1);
    %I = I - D_t;
 end

    disp('')

elseif strcmp(version, 'test7') % this works

    % %removal of mean profile of dark signal
    % I = I - d_x;
    %I = data.light + data.dark;
    %I = movmean(I, 16, 2);

    %Im = movmean(I,16,2);

    dI = I(2:end,:)./I(1:end-1,:);
    dIm = movmean(dI, 2*Wx + 1, 2);
    dC = dI./dIm;
    C = cumprod([ones(1,Nx); dC],1);

    C = imgaussfilt(C,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]); 
    

    if strcmp(params.analysis.removeBackground_Light_maskT, 'on') && nargin == 3
        Cm = C;
        Mask0 = not(imdilate(not(Mask),ones(params.Wx)));
        Cm(~Mask0) = NaN;
        Cm = movmean(Cm, 2*params.Wt + 1, 1);
        Cm = interpolateNaNs(Cm,1);
    else
        Cm = movmean(C, 2*params.Wt + 1, 1);
    end

    C = C./Cm;
    C = C - 1;

    %disp('')



elseif strcmp(version, 'test6')

    %removal of mean profile of dark signal
    %I = I - d_x;

    %removal of light profile shift + intensity jump + dak signal jump
    Im = movmean(I,16,2);
    Im = Im(:,9:Nx-7);
    dIm = Im(:,1:end-2) - Im(:,3:end);
    Im = Im(:,2:end-1);
    I = I(:,10:Nx-8);

    %solve equation Im(i+1,:) = b_t*Im(i,:) + delta*dIm(i,:) + d_t 
    s = ones(3,Nt-1);
    for i = 1:Nt-1
        %s(:,i) = [Im(i,:)', dIm(i,:)', ones(Nx-17,1)] \ Im(i+1,:)';
        s(:,i) = [I(i,:)', dI(i,:)', ones(Nx-17,1), I(i,:)] \ I(i+1,:)';
        %Im(i+1:end,:) = Im(i+1:end,:) - s(3);
    end

    b_t = s(1,:)';
    %delta_t = s(2,:)'.*dIm(i,:);
    delta_t = s(2,:)'.*dI(i,:);
    d_t = s(3,:)';

    epsilon = (Im(2:end,:) - d_t - delta_t)./(b_t.*Im(1:end-1,:));
    C = (I(2:end,:) - d_t - delta_t)./(b_t.*Im(1:end-1,:));

    disp('')

elseif strcmp(version, 'test5')

    I = I - d_x;
    I_filtr = imgaussfilt(I,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]); 

    B_x = ones(1,Nx);
    R0 = 0; R = Inf;
    for iter = 1:10
        B_t = movmean(I_filtr./B_x, Wx + 1, 2);
        B_x = movmean(I_filtr./B_t, Wt + 1, 1);
        R0 = R;
        R = I_filtr - B_t.*B_x;
    end

    %dR = diff(R,1,2);
    R2 = ones(size(R));
    for i=1:16
        A(:,i) = mean(dR(:,i:16:end),2);
        Astd(:,i) = std(R(:,i:16:end),1,2);
        R2(:,i:16:end) = R(:,i:16:end)- A(:,i);
    end

    %R_std = 


    disp('')

elseif strcmp(version, 'test4')

    %removal of mean profile of dark signal
    %I = I - d_x;
    I = I - mean(data.dark,1);

    
    %removal of light profile shift + intensity jump + dak signal jump
    Im = movmean(I,16,2);
    Im = Im(:,9:Nx-7);
    dIm = Im(:,1:end-2) - Im(:,3:end);
    Im = Im(:,2:end-1);
    %I = I(:,10:Nx-8);

    % Mask
    W = ones(size(Mask));
    W(Mask) = NaN;
    W = movmean(W,16,2);
    W = W(:,10:Nx-8);
    W = isnan(W(1:end-1,:)) & isnan(W(2:end,:));
    W = double(W);


    D = zeros(Nt,1);
    for iter = 1:10

    %I2 = s(1,1)*I1 + s(2,1)*dI1 

    %solve equation Im(i+1,:) = a*Im(i,:) + b*dIm(i,:) + c 
    % Im = A*I1 + D;
    s = ones(3,Nt);
    %A = ones(Nt,1);
    %a = ones(Nt,1);
    %d = zeros(Nt, Nx-17);
    %D = zeros(Nt,Nx-17);
    %C = zeros(Nt,1);
    %D = zeros(Nt,1);
    d = zeros(Nt,1);
    for i = 1:Nt-1
        %s(:,i) = [Im(i,:)'-D(i), dIm(i,:)', ones(Nx-17,1)] \ (Im(i+1,:)'-D(i+1));
        %s(:,i) = [Im(i,W(i,:))'-D(i), dIm(i,W(i,:))', ones(sum(W(i,:)),1)]
        %\ (Im(i+1,W(i,:))'-D(i+1)); %this works with W logical
        s(:,i) = (W(i,:)'.*[Im(i,:)'-D(i), dIm(i,:)', ones(Nx-17,1)]) \ (W(i,:)'.*(Im(i+1,:)'-D(i+1)));
        d(i+1) = s(3,i);
        %d = s(3);
        %s = [Im(i,:)', ones(Nx-17,1)] \ Im(i+1,:)';
        %A(i+1) = s(1)*A(i);
        %d = s(2)*dIm(i,:) + s(3);
        %d = s(2);
        %D(i+1,:) = s(1)*D(i,:) + s(3);
        %C(i+1) = s(3);%s(1)*C(i) + s(3);
    end

    D2 = cumsum(d);
    D2 = D2 - mean(D2);
    D = D + D2;


    plot(D); hold on
    plot(mean(data.dark - mean(data.dark,1),2))

    end

    

elseif strcmp(version, 'test3')

    I = data.light;

    Wx = params.Wx;
    Wt = params.Wt;

    B_x = ones(size(I));
    R = 0; R0 = Inf;
    %while sum(abs(R-R0) > threshold)
    for iter = 1:100    
        B_t = movmean(I./B_x, 2*Wx+1, 2);
        B_x = movmean(I./B_t, 2*Wt + 1, 1);
        R0 = R;
        R = I - B_t.*B_x;
    end

    

   

elseif strcmp(version, 'test2')

    %d_x = mean(data.dark,1);
    D = d_x;
    d_t = 0;
    W = 0.8*ones(Nt, Nx - 17);
    epsilon_t = ones(Nt, Nx - 17);
    C = Inf(Nt, Nx - 17);
    for iter = 1:10
        L = I - D;
    
        %Im = movmean(data.light,16,2);
        Im = movmean(L,16,2);
        Im = Im(:,9:Nx-7);
        dIm = Im(:,1:end-2) - Im(:,3:end);
        Im = Im(:,2:end);
    
        %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
        a = zeros(16, Nx);
        for i = 1:16
            a(i,i:16:end) = 1;
        end
        a0 = a(:,10:Nx-8);
    
        L0 = L(:,10:Nx-8);
        
        %solve equation Im(i+1,:) = a*Im(i,:) + b*dIm(i,:) + c
        d_t0 = d_t;
        d_t = zeros(Nt, 16);
        dL0 = ones(size(L0));
        %W2 = sqrt(W(1:end-1,:).*W(2:end,:));
        for i = 1:Nt-1
    
            %s = (W2(i,:)'.*[L0(i,:)', dIm(i,:)', a0']) \ (W2(i,:)'.*L0(i+1,:)');
            s = [L0(i,:)', dIm(i,:)', a0'] \ L0(i+1,:)';
            d_t(i+1,:) = s(3:end)';
            dL0(i+1,:) = L0(i+1,:)./(s(1)*L0(i,:) + s(2)*dIm(i,:) + s(3:end)'*a0);
            % s = [Im(i,:)', dIm(i,:)', ones(Nx-17,1)] \ Im(i+1,:)';
            % d0 = Im(i,:)./Im(i+1,:);
            % d1 = Im(i+1,:)./(s(1)*Im(i,:) + s(2)*dIm(i,:) + s(3));
            % c(i) = s(3);
        end

        d_t = cumsum(d_t,1);
        d_t = d_t - mean(d_t,1);
        d_t = d_t + d_t0;
    
        Dd = d_t*a;
        D = Dd + d_x;

        R = cumprod(dL0,1);
        R_filtr = imgaussfilt(R,[eps, params.wx+eps],'FilterSize',[1,2*ceil(3*(params.wx+eps))+1]); 

        % % without weigthing
        % epsilon_x = movmean(R_filtr,2*Wt+1,1);
        % epsilon_t = movmean(R./epsilon_x, 2*Wx+1,2);

        
        % with weigthing
        Wt1 = Wt;
        relevant = true(1, size(R,2));
        B = R_filtr./epsilon_t.*W;
        epsilon_x = NaN(size(R));
        while sum(relevant) > 0
            A = movsum(W, 2*Wt1 + 1, 1);
            epsilon_x0 = movsum(B, 2*Wt1 + 1, 1)./A;
            ind = A >= 0.8*Wt & isnan(epsilon_x);
            epsilon_x(ind) = epsilon_x0(ind);
            if Wt1 == Wt
                epsilon_x([1:Wt, end-Wt:end],:) = epsilon_x0([1:Wt, end-Wt:end],:);
            end
            relevant = sum(isnan(epsilon_x), 1) > 0;
            Wt1 = Wt1 + 1;
        end

        Wx1 = Wx;
        relevant = true(size(R,1), 1);
        B = R_filtr./epsilon_x.*W;
        epsilon_t = NaN(size(R));
        while sum(relevant) > 0
            A = movsum(W, 2*Wx1 + 1, 2);
            epsilon_t0 = movsum(B, 2*Wx1 + 1, 2)./A;
            ind = A >= 0.8*Wx & isnan(epsilon_t);
            epsilon_t(ind) = epsilon_t0(ind);
            if Wx1 == Wx
                epsilon_t(:,[1:Wx, end-Wx:end]) = epsilon_t0(:,[1:Wx, end-Wx:end]);
            end
            relevant = sum(isnan(epsilon_t), 2) > 0;
            Wx1 = Wx1 + 1;
        end

        C0 = C;
        C = R_filtr./epsilon_x./epsilon_t;
        I_std = STD_profile(C - 1);
        W = exp(-0.5*((C - 1)./I_std).^2); 

        % C = C./movmean(C,2*Wx+1,2);
        % C = C./movmean(C, 2*Wt+1,1);
    
        % plot(d_t(:,1),'Marker','.'); hold on
        % plot(d_t_test(:,1))
         disp('')
    end

elseif strcmp(version, 'test1')

    %% Build FPN basis A (16 x Nx) where row k has 1 at indices congruent k mod 16
    a = zeros(16, Nx);
    for i = 1:16
        a(i,i:16:end) = 1;
    end

    %tohle dat pryc
    %I = data.light + data.dark;
    
    

    b_t = ones(Nt,1);
    R0 = Inf(Nt,Nx);
    R = ones(Nt, Nx);
    I_std = 1;

    b_x = mean(I - d_x,1);

    while sum(abs(R0 - R)./I_std > threshold,'all') > 0
    
        R0 = R;
        
         %% For each frame t solve linear system: I(t,:) = b_x*b_t(t,:) + d_t(t,:)*a + d_x;
        % Unknown vector s = [b_t(t); d_t(t,:)] length 17
        % Can be written as I(t,:)' = A * s', where A = [b_x', a']

        s = ones(17, Nt);
        A = [b_x', a'];
        B = (I - d_x)';
        W = 1./b_x;%sqrt(b_x);
        A = W'.*A;
        B = W'.*B;
        for i = 1:Nt
            s(:,i) = A \ B(:,i);
        end
        b_t = s(1,:)';
        d_t = s(2:17,:)';

        % figure
        % imagesc(data.dark - d_t*a -d_x); colorbar
        % figure
        % plot(d_x - mean(data.dark,1))

        % %% For each frame t solve linear system: I(t,:) = b_x*b_t(t,:) + d_t(t,:)*a + d_x;
        % % Unknown vector s = [b_x(x); d_x(x)] 
        % % Can be written as I - d_t*a = A * s', where A = [b_t; 1]
        % 
        % s = ones(2, Nx);
        % A = [b_t, ones(Nt,1)];
        % B = I - d_t*a;
        % for i = 1:Nx
        %     s(:,i) = A \ B(:,i);
        % end
        % b_x = s(1,:);
        % d_x = s(2,:);
        % 
        %% Reconstruct background fields B and D
        B = b_x.*b_t;     
        D_t = d_t*a;  

        R = (I - D_t - d_x)./B;

        
        %close all
        % figure
        % for i = 1:16
        %     subplot(4,4,i)
        %     % plot(d_t_test(:,i),'Marker','o'); hold on
        %     % plot(d_t(:,i),'Marker','.')
        %     plot(d_t_test(:,i) - d_t(:,i))
        % end
        % figure
        % imagesc(data.dark - d_t*a -d_x); colorbar
        % figure
        % plot(d_x - mean(data.dark,1))
        % figure
        % plot(mean(d_t,2)); hold on
        % plot(mean(d_t_test,2))

        I_std = STD_profile(R - 1);
    end

    figure
    subplot(1,2,1)
    imagesc(R); colorbar
    subplot(1,2,2)
    plot(std(R,1,1))

    disp('')


elseif strcmp(version, 'without weightening')

    %%%%% withour dark signal
    epsilon_t = ones(Nt, Nx);
    epsilon_x = ones(Nt, Nx);
    C0 = Inf(Nt,Nx);
    C = ones(Nt, Nx);
    I_std = 1;
    kk = 0;
    while sum(abs(C0 - C)./I_std >= params.iterationThreshold, 'all') > 0 && kk < 50
    
        C0 = C;
        kk = kk+1;
    
        epsilon_t = movmean(I./epsilon_x, 2*params.Wx + 1, 2)./movmean(W, 2*params.Wx + 1, 2);
        epsilon_x = movmean(I./epsilon_t, 2*params.Wt + 1, 1)./movmean(W, 2*params.Wt + 1, 1);
    
        C = I./epsilon_x./epsilon_t;
        I_std = STD_profile(C - 1);
        % W = exp(-0.5*((C - 1)./I_std).^2); 
    
    end
    if sum(abs(C0 - C) > params.iterationThreshold) > 0
        disp('removeBackground_light: did not converge')
    end

elseif strcmp(version, 'with weightening')

    Wx = params.Wx;
    Wt = params.Wt;
    
    t = 1+Wt:Nt-Wt;
    x = 1+Wx:Nx-Wx;
    [x,t] = meshgrid(x,t);
    x2 = repmat(x,1,1,2*Wt+1, 2*Wx+1);
    t2 = repmat(t,1,1,2*Wt+1, 2*Wx+1);
    x2 = x2 + permute([-Wx:Wx]',[4,3,2,1]);
    t2 = t2 + permute([-Wt:Wt]',[3,2,1]);
    ind_x = sub2ind([Nt,Nx],t2_x,x2_x);
    A = I(ind_x);
    Im_x = mean(A,3);

    % plot(Im_x(100,:))
    % hold on
    % plot(Im_x_test(100+Wt,Wx+1:Nx-Wx))

end

%%%%%%



%C = C - 1;

% epsilon_t = ones(Nt, Nx);
% C0 = Inf(Nt,Nx);
% C = ones(Nt, Nx);
% while sum(abs(C0 - C) > threshold) > 0
% 
%     C0 = C;
%     epsilon_x = movmean(IMasked./epsilon_t,2*params.Wt + 1, 1,'omitnan');
%     epsilon_t = movmean(IMasked./epsilon_x,2*params.Wx + 1, 2,'omitnan');
%     C = I./epsilon_x./epsilon_t;
% 
% end
% 
% C = C - 1;

   
% %% Package results
% result.C = C;
% result.epsilon_x = epsilon_x;
% result.epsilon_t = epsilon_t;


function I_std = STD_2Dprofile(I, N)

%Itemp = I;

a = I < 0;
I(a) = NaN;
%I_std = sqrt(sum(I.^2,1,'omitnan')./(size(I,1)- sum(a,1)));
I2 = movmean(I.^2,2*N+1,1,'omitnan');
%no = size(I,1) - movmean(a,N)*N;
I_std = sqrt(I2);

% I_std_contr = zeros(size(I_std));
% for i=1:size(I,2)
%     for j=1:size(I,1)
%         a = max([1,j-N]): min([size(I,1), j+N]);
%         I0 = Itemp(a,i);
%         I0(I0<0) = [];
%         I_std_contr(j,i)= sqrt(mean(I0.^2));
%     end
% end
% 
% plot(I_std,'.'); hold on
% plot(I_std_contr,'o')

end

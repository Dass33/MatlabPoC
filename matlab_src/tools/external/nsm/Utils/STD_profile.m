function I_std = STD_profile(I)

a = I < 0;
I(a) = NaN;
%I_std = sqrt(sum(I.^2,1,'omitnan')./(size(I,1)- sum(a,1)));
%I2 = mean(I.^2,1,'omitnan');
I_std = sqrt(mean(I.^2,1,'omitnan'));

b = find(I > 3*I_std);
while isempty(b) == 0
    I(b) = NaN;
    I_std = sqrt(mean(I.^2,1,'omitnan'));
    b = find(I > 3*I_std);
end






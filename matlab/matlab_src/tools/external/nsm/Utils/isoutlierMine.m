function outlier = isoutlierMine(A, minIncluded)

outlier = true(size(A));

m = median(A);
dm = abs(A-m);

[~,ind] = sort(dm);
A = A(ind);

minNumber = ceil(length(A)*minIncluded);
outlier(1:minNumber) = false;
meanA = mean(A(1:minNumber));
stdA = std(A(1:minNumber));

i = minNumber + 1;
outlier(i) = abs(A(i) - meanA) > 3*stdA;
while outlier(i) == false && i < length(A)
    i = i +1;
    outlier(i) = abs(A(i) - meanA) > 3*stdA;
    meanA = mean(A(1:i));
    stdA = std(A(1:i));
end

outlier(ind) = outlier;



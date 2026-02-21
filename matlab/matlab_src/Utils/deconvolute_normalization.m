function s = deconvolute_normalization(Y, W)

[Nt, Nx] = size(Y);
s = NaN(Nt,Nx);

A = eye(Nx,Nx);
B = imdilate(A,ones(1,2*W+1));
B = B./sum(B,2);

for i = 1:Nt

    C = Y(i,:)'.*B-A;
    s(i,:) = linsolve([C; ones(1,Nx)], [zeros(Nx,1);1]);
    

end

s = s./median(s,2);




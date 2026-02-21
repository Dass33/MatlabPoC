function B = movmean_weighted(A, W, dim)

W1 = W(1); W2 = W(2);
B0 = movmean(A, W, dim);
C0 = A./B0 - 1;

C_std = STD_profile(C0);

Z1 = movsum(exp(-0.5*(C0./C_std).^2), [W1 0], dim);
Z2 = movsum(exp(-0.5*(C0./C_std).^2), [0 W2], dim);

%%not finished!




function [C] = removeBackground(I, Wt, Wx)

C = I./movmean(I, 2*Wx+1,2);
%C = C./smoothdata(C,1,'rlowess', 2*setting_0.Wt+1);
C = C./movmedian(C,2*Wt+1,1);
C = C - 1;

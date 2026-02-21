
%% First-pass
figure
imagesc(data.Im)
colormap bone
colorbar
title('I')

figure
imagesc(resultR1.B)
colormap bone
colorbar
title('B_1')

figure
imagesc(repmat(resultR1.b_x, size(resultR1.R,1),1))
colormap bone
colorbar
title('b_x')

figure
imagesc(repmat(resultR1.b_t, 1, size(resultR1.R,2)))
colormap bone
colorbar
title('b_t')

figure
imagesc(resultR1.R)
colormap bone
colorbar
title('R_1')

figure
imagesc(repmat(d_x, size(resultR1.R,1),1))
colormap bone
colorbar
title('d_x')

figure
imagesc(resultR1.D_t)
colormap bone
colorbar
title('D1_t')

figure
imagesc(resultR1.D_t + d_x)
colormap bone
colorbar
title('D1')

figure
imagesc(R1_filt); hold on
colormap bone
colorbar
title('R_1^f')

figure
imagesc(resultC1.epsilon); hold on
colormap bone
colorbar
title('\epsilon_1')

figure
imagesc(resultC1.C); hold on
colormap bone
colorbar
title('C_1')


%% Masking
figure
imagesc(resultC1.C); hold on
colormap bone
colorbar
for it=1:length(PARTICLES)
    plot(PARTICLES(it).position, PARTICLES(it).timeFrame,'Marker','.','Color','white')
end
title('Particle trajectory')

figure
imagesc(not(Mask)); hold on
colormap bone
colorbar
title('Mask')
        

%% Second-pass

figure
imagesc(resultR2.B)
colormap bone
colorbar
title('B_2')

figure
imagesc(repmat(resultR2.b_x, size(resultR2.R,1),1))
colormap bone
colorbar
title('b_x')

figure
imagesc(repmat(resultR2.b_t, 1, size(resultR2.R,2)))
colormap bone
colorbar
title('b_t')

figure
imagesc(resultR2.R)
colormap bone
colorbar
title('R_2')

figure
imagesc(repmat(d_x, size(resultR2.R,1),1))
colormap bone
colorbar
title('d_x')

figure
imagesc(resultR2.D_t)
colormap bone
colorbar
title('D2_t')

figure
imagesc(resultR2.D_t + d_x)
colormap bone
colorbar
title('D2')

figure
imagesc(R2_filt); hold on
colormap bone
colorbar
title('R_2^f')

figure
imagesc(resultC2.epsilon); hold on
colormap bone
colorbar
title('\epsilon_2')

figure
imagesc(resultC2.C); hold on
colormap bone
colorbar
title('C_2')

function scatter_plot(A, B, n, labelA, labelB)

%figure
for i=1:length(A)
         scatter(A(i),B(i),'MarkerFaceAlpha',n(i)/max(n),...
               'MarkerFaceColor','red',...
               'MarkerEdgeColor','none'); hold on
end
xlabel(labelA)
ylabel(labelB)

return

%% scatter plot
figure
for i=1:length(iOC)
         scatter(iOC(i)*1e3,D(i),'MarkerFaceAlpha',n(i)/max(n),...
               'MarkerFaceColor','black',...
               'MarkerEdgeColor','none'); hold on
end
xlabel('iOC (nm)')
ylabel('Diffusivity (um^2/s)')


return

%% scatter plot
figure;
for i=1:length(MW)
     scatter(MW(i),HR(i),'MarkerFaceAlpha',n(i)/max(n),...
             'MarkerFaceColor','black',...
             'MarkerEdgeColor','none'); hold on
end
xlabel('Molecular weight (kDa)')
ylabel('Hydrodynamic radius (nm)')
xlim([MW_edges(1) MW_edges(end)])
ylim([HR_edges(1) HR_edges(end)])




%% add theoretical MWxHR curve for a liposome
eps1 = 1.33^2; %inner core
eps2 = 1.48^2; %outer shell
epsm = 1.33^2; %medium
r = linspace(0,0.1); %radius of the whole particle
V = 4/3*pi*r.^3; %the whole volume of a particle
dch = 4.9e-3; %thickness of the shell
f = ((r-dch)./r).^3; %fraction of the core volume
alpha = alpha_sphere_coreshell(V,f,eps1,eps2,epsm);%polarizability
alpha_MW = 0.461e-12;
iOC_liposome = -alpha/calibration/alpha_MW*1e3;

%MW_liposome = alpha/alpha_MW/1e3; %[kDa] molecular weight
%[iOC_anal,calibration] = WeightToiOC (weight, nanochannelArea);
plot(iOC_liposome,r*1e3,'Color','black')

%%
r = linspace(10e-3,0.1); %radius of the whole particle
dch = 4.9e-3; %thickness of the shell
V = 4/3*pi*(r.^3 - (r-dch).^3); %the whole volume of the shell
Vsp = 0.7446  *1e-3 *1e-3 * 1e18; %mean specific volume [mL/g *1e-3 *1e-3 * 1e18 = um^3/g]
MW_liposome = V/Vsp; %mass of one liposome
NA = 6.023e23; %Avogadro number (1/mol)
MW_liposome = MW_liposome*NA/1e3; %mass of one mol of liposomes [kDa = kg/mol]
plot(MW_liposome,r*1e3)

%% effective refractive index of vesicles
n_m=1.33;
n_c=1.46; 
n_mean = (3*n_m^2 + n_c^2)/(n_m^2 - n_c^2)/2;
alpha = -iOC*1e-3*nanochannelArea/n_mean;
V=4/3*pi*(HR*1e-3).^3;
RI_eff = n_m.*sqrt((2*alpha + 3*V)./(3*V-alpha));

%%
figure;
for i=1:length(MW)
                scatter(iOC(i), RI_eff(i),'MarkerFaceAlpha',n(i)/max(n),...
                    'MarkerFaceColor','black',...
                    'MarkerEdgeColor','none'); hold on
end
xlabel('Integrated optical contrast (nm)')
ylabel('Effective refractive index')

%%
figure;
for i=1:length(MW)
                scatter(HR(i), RI_eff(i),'MarkerFaceAlpha',n(i)/max(n),...
                    'MarkerFaceColor','black',...
                    'MarkerEdgeColor','none'); hold on
end
xlabel('Hydrodynamic radius (nm)')
ylabel('Effective refractive index')


%% add theoretical MWxHR curve for globular protein
MW_globular = linspace(1e3,2e4);
HR_globular = massToHR (MW_globular*1e3,'globular')*1000; %[nm]
plot(MW_globular,HR_globular)



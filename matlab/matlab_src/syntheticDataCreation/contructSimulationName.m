function [simulationSizeFolder, name] = contructSimulationName(simulated, iN,fun)

simulationSizeFolder = strcat(num2str(simulated.number_frames),'x',num2str(simulated.number_pixels),'_DLS', num2str(simulated.DLS),'_Dt', num2str(round(simulated.Dt*1e3)/1e3), 'Dx', num2str(round(simulated.Dx*1e4)/1e4));

        switch fun

            case 'diffusing_molecules'

                name = strcat('D',num2str(simulated.D_um2s),'_conc',num2str(simulated.concentration),'_',num2str(iN));

            case 'flowing_molecules'

                name = strcat('velocity',num2str(simulated.velocity_ums),'_D',num2str(simulated.D_um2s),'_conc',num2str(simulated.concentration),'_',num2str(iN));  

            case 'diffusing_in_trap'

                name = strcat('D',num2str(simulated.D_um2s),'_',num2str(iN));

            case 'flow_direction_change'  

                name = strcat('velocity_',num2str(simulated.velocity_ums),'_timespam_',num2str(simulated.timespam_s),'_D',num2str(simulated.D_um2s),'_conc',num2str(simulated.concentration),'_',num2str(iN)); 
                
        end

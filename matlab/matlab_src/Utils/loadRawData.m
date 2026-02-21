function data = loadRawData(name, dataType)



switch dataType

    case 'tiff2' %all frames are avegared over ROI_height and FrameCombine, new format of txt file, includes reading of temperature
        
        filename = strcat(name, '.tiff');
        data.Im = imread(filename);

        filename = strcat(name, '.txt');
        lines = readcell(filename);
        FPS = lines{6,2};
        data.TemperatureStart = str2double(lines{19,2}(1:end-2));
        data.TemperatureEnd = str2double(lines{20,2}(1:end-2));
        data.Dt = 1/FPS;
        data.Dx = 6.6/100;
        

    case 'tiff1' %all frames are avegared over ROI_height and FrameCombine
        
        filename = strcat(name, '.tiff');
        data.Im = imread(filename);

        filename = strcat(name, '.txt');
        lines = readcell(filename);
        a = strfind(lines{1},'-');
        FPS = str2double(lines{1}(a(4)+7:a(5)-1));
        data.Dt = 1/FPS;
        data.Dx = 6.6/100;    


    case 'tiff3' %all frames are saved, I want to average over FrameCombine, i.e. the resuls is matrix [Ny, Nx, Nt]
        
        filename = strcat(name, '.txt');
        lines = readcell(filename);
        FPS = lines{6,2};
        Ny = lines{13,2};
        data.TemperatureStart = str2double(lines{19,2}(1:end-2));
        data.TemperatureEnd = str2double(lines{20,2}(1:end-2));
        data.Dt = 1/FPS;
        data.Dx = 6.6/100;

        filename = strcat(name, '.tiff');
        info = imfinfo(filename);
        Nx = info(1).Width;
        Nt = length(info)
        
        I = zeros(Ny, Nx, Nt);
        for i = 1:size(I,3)
            a = imread(filename, i);
            a = reshape(a,Ny,info(1).Height/Ny,Nx);
            a = mean(a,2);
            I(:,:,i) = permute(a,[1,3,2]);
        end

        data.I = I;


    case 'mat'

        %load(strcat(name,'_M.mat'))
        load(strcat(name,'.mat'))
        if not(isfield(data,'Dx'))
            data.Dx = data.Yum(2) - data.Yum(1);
            data.Dt = data.time(2) - data.time(1);
        end

    case 'mat from Chalmers'

        load(strcat(name,'_M.mat'))

        C = who;

        for i=1:length(C)
            data.(C{i}) = eval(C{i});
        end
        
        data.Im=double(data.Im);
        data.Im=permute(data.Im,[1,3,2]);
        data.time = time;
        data.Yum = Yum;
end



%     if size(data.Im,2)==length(data.time)
%         disp('changing dimensions of data.Im!')
%         data.Im=data.Im';
%     end


%     %% exclude zero intensity frames
%     ff=find(mean(data.Im,2)==0);
%     if isempty(ff) == 0
%         display(strcat('darkness at frame no',num2str(ff)));
%         data.time(ff)=[];
%         data.Im(ff,:)=[];
%     end

%     %% add missing fields
%         fieldname = fieldnames(data);
% 
%         a = strfind(fieldname,'pixelSize');
%             a = cellfun(@length, a);
%             if sum(a) == 0
%                 data.pixelSize = 6.6;
%             end
% 
% %             a = strfind(fieldname,'time');
% %             a = cellfun(@length, a);
% %             if sum(a) == 0
%                 data.time = (1:size(data.Im,1))/data.frameRate;
% %             end
% 
% %             a = strfind(fieldname,'Yum');
% %             a = cellfun(@length, a);
% %             if sum(a) == 0
%                 data.Yum = (1:size(data.Im,2))*data.pixelSize/data.magnification;
% %             end



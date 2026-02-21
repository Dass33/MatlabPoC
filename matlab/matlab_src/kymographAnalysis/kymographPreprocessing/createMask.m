function Mask = createMask(I, PARTICLES, version, denoise_setting)

% this function associates pixels and frames with particle's image

% input:
% I - intensity matrix
% [PARTICLES.timeFrame, PARTICLES.position] - coordinates of local minimas corresponding to the particles
% version: condition under which algotihm decides which pixels nad frames are associated with particle's image
%   version = 'negative values' - all spatial coordinates around [PARTICLES.timeFrame, PARTICLES.position] for which intensity values did not exceed zero 
%   version = 'width estimation' - this version estimates span of pixels
%   and frames with particle's image from particles' movement between the
%   frames ad expected RMS width of the stationary particle image (denoise_setting.ws*sqrt(2))

% output
% Mask is a matrix of size(I)
% Mask = true for coordinates not associated with the particle's image 
% Mask = false for coordinates associated with the particle's image 

[Nt, Nx] = size(I);


if strcmp(version, 'negative values') == 1 

    Mask = true(Nt, Nx);

    timeFrame = []; position = [];
    for i = 1:length(PARTICLES)
        timeFrame = [timeFrame; PARTICLES(i).timeFrame];
        position = [position; PARTICLES(i).position];
    end
    
    ind = sub2ind(size(I),timeFrame, position);
    Mask(ind) = false;
    
    %adding pixels to the right from the minimum position 
    a = ind;
    while isempty(a) == 0 
    
          [a1,a2] = ind2sub(size(I),a);
          i = a2+1 <= size(I,2);
          a1 = a1(i); a2 = a2(i); a = a(i);
          b = sub2ind(size(I),a1,a2+1);
          %i = (I(b) < 0 & I(a) < 0) | (I(b) > 0); %for double peak and dip 
          i = I(b) < 0; %for dip
          a = b(i); 
          Mask(a) = false;
    
    end
    
    %adding pixels to the length from the minimum position 
    a = ind;
    while isempty(a) == 0 
    
          [a1,a2] = ind2sub(size(I),a);
          i = a2-1 >= 1;
          a1 = a1(i); a2 = a2(i); a = a(i);
          b = sub2ind(size(I),a1,a2-1);
          %i = (I(b) < 0 & I(a) < 0) | (I(b) > 0); %for double peak and dip 
          i = I(b) < 0; %for dip
          a = b(i); 
          Mask(a) = false;%I(a);
    
    end

elseif strcmp(version, 'negative and positive values') == 1 

    Mask = true(Nt, Nx);

    timeFrame = []; position = [];
    for i = 1:length(PARTICLES)
        timeFrame = [timeFrame; PARTICLES(i).timeFrame];
        position = [position; PARTICLES(i).position];
    end
    
    ind = sub2ind(size(I),timeFrame, position);
    Mask(ind) = false;
    
    %adding pixels to the right from the minimum position 
    a = ind;
    while isempty(a) == 0 
    
          [a1,a2] = ind2sub(size(I),a);
          i = a2+1 <= size(I,2);
          a1 = a1(i); a2 = a2(i); a = a(i);
          b = sub2ind(size(I),a1,a2+1);
          i = (I(b) < 0 & I(a) < 0) | (I(b) > 0); %for double peak and dip 
          %i = I(b) < 0; %for dip
          a = b(i); 
          Mask(a) = false;
    
    end
    
    %adding pixels to the length from the minimum position 
    a = ind;
    while isempty(a) == 0 
    
          [a1,a2] = ind2sub(size(I),a);
          i = a2-1 >= 1;
          a1 = a1(i); a2 = a2(i); a = a(i);
          b = sub2ind(size(I),a1,a2-1);
          i = (I(b) < 0 & I(a) < 0) | (I(b) > 0); %for double peak and dip 
          %i = I(b) < 0; %for dip
          a = b(i); 
          Mask(a) = false;%I(a);
    
    end    

elseif strcmp(version, 'width estimation from movement & ws') == 1 | strcmp(version, 'width estimation from movement & ws & Wx') == 1

    Mask = false(Nt, Nx);
    if strcmp(version, 'width estimation from movement & ws') == 1
        Wmask = ceil(3*denoise_setting.ws*sqrt(2));
    elseif strcmp(version, 'width estimation from movement & ws & Wx') == 1
        Wmask = ceil(3*denoise_setting.ws*sqrt(2)) + denoise_setting.Wx;
    end

        % Mask the trajectories
        for i=1:length(PARTICLES)

          for j = 1:length(PARTICLES(i).timeFrame)  

            if j == 1

                position1 = PARTICLES(i).position(j) - (PARTICLES(i).position(j+1) - PARTICLES(i).position(j));
                position2 = PARTICLES(i).position(j);
                position3 = PARTICLES(i).position(j+1);

            elseif j == length(PARTICLES(i).timeFrame)

                position1 = PARTICLES(i).position(j-1);
                position2 = PARTICLES(i).position(j);
                position3 = PARTICLES(i).position(j) + (PARTICLES(i).position(j) - PARTICLES(i).position(j-1));

            else

                position1 = PARTICLES(i).position(j-1);
                position2 = PARTICLES(i).position(j);
                position3 = PARTICLES(i).position(j+1);

            end

            it = PARTICLES(i).timeFrame(j);
            ix = max([min([position1, position2, position3]), 1]) :...
                     min([max([position1, position2, position3]), Nx]);

            Mask(it, ix) = true;

          end

        end

        % Expand to account for the width of DLS
        Mask = imdilate(Mask, ones(1,2*Wmask+1));
        Mask = not(Mask);



end
    

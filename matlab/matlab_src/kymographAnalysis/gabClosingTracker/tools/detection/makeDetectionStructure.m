function Detections = makeDetectionStructure(thresholded, localMinimas, Y, noise_std, pfa)

    mask = thresholded & localMinimas;

    [Detections.position, Detections.frame] = find(mask.');

    Detections.nDetections = length(Detections.frame);

    Detections.intensity = Y(sub2ind(size(Y), Detections.frame, Detections.position));
    
    Detections.noise_std = noise_std;

    Detections.snr = abs(Detections.intensity) / noise_std;

    Detections.pfa = pfa;

end
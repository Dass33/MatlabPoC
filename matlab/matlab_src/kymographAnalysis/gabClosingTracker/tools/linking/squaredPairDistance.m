function D = squaredPairDistance(v,w)

    % Analogy to pdist2 from Statistics and Machine Learning Toolbox. Input
    % vectors are assumed to be column vectors.

    D = ( v - w.' ).^2;

end
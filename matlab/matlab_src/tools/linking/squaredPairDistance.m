% Analogy to pdist2 from Statistics and Machine Learning Toolbox. Input
% vectors are assumed to be column vectors.

function D = squaredPairDistance(v,w)

    D = ( v - w.' ).^2;

end
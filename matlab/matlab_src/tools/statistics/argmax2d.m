function [i1,i2] = argmax2d(X)

    [~,index] = max(X,[],"all","linear");
    [i1,i2] = ind2sub(size(X),index);

end
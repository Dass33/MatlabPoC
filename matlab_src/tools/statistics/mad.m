function y = mad(x)

    M = median(x(:));

    y = median( abs( x(:)-M ) );

end
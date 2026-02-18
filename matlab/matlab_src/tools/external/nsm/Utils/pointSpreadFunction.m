function y = pointSpreadFunction(x,a,b,c,Wx)

    %dx = x(2)-x(1);
    Wx = round(Wx);
    x0 = [x(1) - (Wx:-1:1)'; x; x(end) + (1:Wx)'];
    y0 = a.*exp(-((x0-b)./c).^2);
    ym = movmean(y0, 2*Wx+1);
    y = y0 - ym;
    y = y(Wx+1:end-Wx);

end
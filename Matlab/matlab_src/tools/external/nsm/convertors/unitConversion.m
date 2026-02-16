function B = unitConversion(A, data, conversion)

switch conversion

    case 'px2 per timeFrame to um2 per second'
        B = A*(data.Yum(2) - data.Yum(1)).^2./(data.time(2)-data.time(1));

    case 'um2 per second to px2 per timeFrame'
        B = A/(data.Yum(2) - data.Yum(1)).^2.*(data.time(2)-data.time(1));    

    case 'px to um'
        B = A*(data.Yum(2) - data.Yum(1));

    case 'um to px'
        B = A/(data.Yum(2) - data.Yum(1));       

    case 'timeFrame to second'
        B = A*(data.time(2) - data.time(1));

     
end
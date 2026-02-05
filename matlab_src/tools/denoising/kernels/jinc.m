function [h,x] = jinc(a, options)

    arguments

        a

        options.x_max = 16.47

    end

    range = ceil( options.x_max/a ); 
    
    x = -range:range;
    
    h = 2*besselj(1,a*x) ./ (a*x);
    
    h(a*x==0) = 1;
      
end
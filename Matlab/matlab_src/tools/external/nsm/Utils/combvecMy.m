
function AB = combvecMy(A,B, dim)

if dim == 2


    A2 = repmat(A,size(B,2),1);
    A2 = reshape(A2,size(A,1),[]);
    
    B2 = repmat(B(:),size(A,2),1);
    B2 = reshape(B2,size(B,1),[]);
    
    
    AB = [A2; B2];

elseif dim == 1

    A2 = repmat(A,size(B,1),1);
    %A2 = reshape(A2,size(A,1),[]);
    
    B2 = repmat(B',size(A,1),1);
    B2 = B2(:);
    
    
    AB = [A2, B2];

end


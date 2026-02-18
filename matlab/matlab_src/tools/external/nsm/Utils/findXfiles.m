function names = findXfiles (folder, X, Y) 

d=dir(folder);
[a1,a2]=cellfun(@size,strfind({d.name},X));
names = {d.name};
names = names(a1==1);
for i=1:length(names)
    names{i}=strcat(names{i}(1:end-length(X)));
end

if nargin == 3
    
    for i=1:length(Y)
        [b1(i,:),b2(i,:)]=cellfun(@size,strfind(names,Y{i}));
    end
    
    names = names(sum(b1,1)==length(Y));

end
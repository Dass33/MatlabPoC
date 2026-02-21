function data = convertTodata(name)

load(name);

C = who;

for i=1:length(C)
    data.(C{i}) = eval(C{i});
end

data.Im=double(data.Im);
data.Im=permute(data.Im,[1,3,2]);
data.time = time;
data.Yum = Yum;


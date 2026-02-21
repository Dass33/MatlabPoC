function POPULATION = analyzePopulation_robustMean(collection, setting)

Properties = setting.properties;
NProperties = length(Properties);
Ntrajectories = length(collection.(Properties{1}));
Y = ones(NProperties, Ntrajectories);
for i = 1:NProperties
    Y(i,:) = collection.(Properties{i});
end

[STD, MEAN, selected] = std_modified_ND(Y, 2, 'multiD', collection.N);
for i = 1:NProperties
    POPULATION.MEAN.(Properties{i}) = MEAN(i);
    POPULATION.STD.(Properties{i}) = STD(i);
    POPULATION.FWHM.(Properties{i}) = 2*sqrt(2*log(2))*POPULATION.STD.(Properties{i});
    POPULATION.RESOLUTION.(Properties{i}) = abs(POPULATION.MEAN.(Properties{i})./POPULATION.FWHM.(Properties{i}));

end

POPULATION.Ntrajectories = sum(selected);
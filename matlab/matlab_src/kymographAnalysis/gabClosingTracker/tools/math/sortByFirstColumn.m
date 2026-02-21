function B = sortByFirstColumn(A)

    [~,sortInd]=sort(A(:,1));
    B = A(sortInd,:);

end
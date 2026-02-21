function DIPSCOMB = evaluateDIPSCOMB(DIPS, DIPSCOMB)

Tlength = size(DIPSCOMB.ind,1);
noDUMMY2 = length(DIPS.position);

% calculate I and Istd
I0 = DIPS.I_norm(DIPSCOMB.ind);
I = mean(I0, 1, 'omitnan');
Istd = std(I0,1,1, 'omitnan');

isDUMMY = DIPS.isDUMMY(DIPSCOMB.ind);
Istd(sum(isDUMMY,1) >= Tlength - 1) = NaN; %std works only for mnimum 2 elements

% calculate D
isDUMMYplus = not(imdilate(not(isDUMMY),ones(3,1)));

position = DIPS.positionRefined(DIPSCOMB.ind);
position(isDUMMYplus) = NaN; %omit positions at DUMMY
Dx = diff(position,1,1);
D = std(Dx, 1, 1,'omitnan');
D(sum(isDUMMYplus,1) >= Tlength - 2) = NaN; %std works only for minimum 2 elements



% collect results
DIPSCOMB.I = I;
DIPSCOMB.Istd = Istd;
DIPSCOMB.D = D;
DIPSCOMB.N = sum(isDUMMY,1);

% omit repeated trajectories, i.e. DIPSCOMB.ind = noDIP
isRepeated = DIPSCOMB.ind(end,:) == noDUMMY2;
DIPSCOMB.I(isRepeated) = NaN;

% omit those trajectories that enter and leave the field of view 
position = DIPS.position(DIPSCOMB.ind);
positionFirstBoundary1 = position == 0;
positionSecondBoundary1 = position == DIPS.sI(2) + 1;
positionFirstBoundary2 = positionFirstBoundary1 | position == 1;
positionSecondBoundary2 = positionSecondBoundary1 | position == DIPS.sI(2);
DpositionFirstBoundary1 = diff(positionFirstBoundary1,1);
DpositionSecondBoundary1 = diff(positionSecondBoundary1,1);
DpositionFirstBoundary2 = diff(positionFirstBoundary2,1);
DpositionSecondBoundary2 = diff(positionSecondBoundary2,1);

isDeserter = (sum(DpositionFirstBoundary1 == -1,1) > 0 & sum(DpositionFirstBoundary1 == 1,1) > 0) | ...
              (sum(DpositionSecondBoundary1 == -1,1) > 0 & sum(DpositionSecondBoundary1 == 1,1) > 0) | ...
              (sum(DpositionFirstBoundary2 == -1,1) > 0 & sum(DpositionFirstBoundary2 == 1,1) > 0) | ...
              (sum(DpositionSecondBoundary2 == -1,1) > 0 & sum(DpositionSecondBoundary2 == 1,1) > 0);

DIPSCOMB.I(isDeserter) = NaN;
DIPSCOMB.ind(end,isDeserter) = noDUMMY2;
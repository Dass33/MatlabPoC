function y_rec = invert_movmean_fft(Y, A, epsilon)
%INVERT_MOVMEAN_FFT  Reconstruct y from Y = y - movmean(y,A)
%
%   y_rec = invert_movmean_fft(Y, A, epsilon)
%
% Inputs:
%   Y       - observed signal (vector)
%   A       - moving average window length (in samples)
%   epsilon - small regularization constant (e.g. 1e-3)
%
% Output:
%   y_rec   - reconstructed y (up to an unknown constant)

    if nargin < 3
        epsilon = 1e-3;
    end

    N = numel(Y);
    Y = Y(:);  % ensure column vector

    % Fourier transform
    Yf = fft(Y);

    % Frequency axis (normalized, cycles/sample)
    f = (0:N-1)' / N;
    f(f > 0.5) = f(f > 0.5) - 1;  % shift to [-0.5, 0.5)

    % Boxcar moving-average frequency response
    % sinc(x) in MATLAB = sin(pi*x)/(pi*x)
    %H = sinc(f * A);
    H = sin(f*A)./(f*A); H(1) = 1;

    % Inversion of (1 - H) with regularization
    denom = 1 - H;
    y_f = Yf ./ (denom + epsilon);

    % Remove DC component (cannot be recovered)
    y_f(1) = 0;

    % Back to spatial domain
    y_rec = real(ifft(y_f));
end
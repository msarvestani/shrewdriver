from __future__ import division
from numpy import zeros, ones
from math import pow, sqrt, exp


def circleGaussianFade(rolloffStartPoint):
    """
    Makes an alpha mask with Gaussian rolloff

    Args:
        rolloffStartPoint: [int] pixel value to start rolloff

    Returns: circular Gaussian mask as a numpy array
    """

    # must be a power of 2. Higher gives nicer resolution but longer compute time.
    maskSize = 512
    sigma = 0.12    # decays nicely to < 1% contrast at the edge
    twoSigmaSquared = 2*pow(sigma, 2)   # handy for later
    
    mask = ones([maskSize, maskSize])

    maskCenter = maskSize / 2
    rolloffStartPx = maskSize / 2 * rolloffStartPoint
    rolloffStartPxSquared = pow(rolloffStartPx, 2)
    rolloffLengthPx = (1 - rolloffStartPoint) * maskSize / 2

    # This is just distance formula calculated a bit faster
    squaredDistances = zeros(maskSize) 
    for i in xrange(0, maskSize):
        squaredDistances[i] = pow(i-maskCenter, 2)
    
    # Fill in alpha values to produce Gaussian rolloff.
    # Note: In PsychoPy, -1 is "nothing", 0 is "half contrast", 1 is "full contrast".
    for i in xrange(0, maskSize):
        for j in xrange(0, maskSize):
            dSquared = squaredDistances[i] + squaredDistances[j]
            if dSquared > rolloffStartPxSquared:
                # we are outside the main circle, so fade appropriately
                fadeProportion = (sqrt(dSquared)-rolloffStartPx) / rolloffLengthPx
                if fadeProportion > 1:
                    # we are outside the circle completely, so we want "nothing" here.
                    mask[i, j] = -1
                else:
                    # input to Gaussian function, in range [0, 0.5]
                    x = fadeProportion / 2
                    alphaValue = exp(-pow(x, 2)/twoSigmaSquared)*2 - 1
                    mask[i, j] = alphaValue
        
    return mask


def circleLinearFade(rolloffStartPoint):
    """
    Makes an alpha mask with linear rolloff

    Args:
        rolloffStartPoint: [int] pixel value to start rolloff

    Returns: circular linear rolloff mask as a numpy array
    """

    # must be a power of 2. Higher gives nicer resolution but longer compute time.
    maskSize = 512
    
    mask = ones([maskSize, maskSize])

    maskCenter = maskSize / 2
    rolloffStartPx = maskSize / 2 * rolloffStartPoint
    rolloffStartPxSquared = pow(rolloffStartPx, 2)
    rolloffLengthPx = (1-rolloffStartPoint)*maskSize/2

    # This is just distance formula calculated a bit faster
    squaredDistances = zeros(maskSize) 
    for i in xrange(0, maskSize):
        squaredDistances[i] = pow(i-maskCenter, 2)
    
    # Fill in alpha values to produce linear rolloff.
    # Note: In PsychoPy, -1 is "nothing", 0 is "half contrast", 1 is "full contrast".
    for i in xrange(0, maskSize):
        for j in xrange(0, maskSize):
            dSquared = squaredDistances[i] + squaredDistances[j]
            if dSquared > rolloffStartPxSquared:
                # we are outside the main circle, so fade appropriately
                fadeProportion = (sqrt(dSquared)-rolloffStartPx) / rolloffLengthPx
                if fadeProportion > 1:
                    # we are outside the circle completely, so we want "nothing" here.
                    mask[i, j] = -1
                else:
                    mask[i, j] = 1 - fadeProportion*2
        
    return mask

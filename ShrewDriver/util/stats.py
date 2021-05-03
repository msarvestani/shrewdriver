from __future__ import division
import sys
sys.path.append("..")

import math
import random
from scipy import stats

def fisherExact(g1r1, g1r2, g2r1, g2r2, nTails=1):
    #returns a p-value
    #Params: group 1 result 1, group 1 result 2, etc.
    
    p = 0
    if nTails == 1:
        pGreater = stats.fisher_exact([[g1r1, g1r2], [g2r1, g2r2]], alternative='greater')[1]
        pLess = stats.fisher_exact([[g1r1, g1r2], [g2r1, g2r2]], alternative='less')[1]
        
        p = pLess
        if pGreater < pLess:
            p = pGreater
    else:
        #default is two tailed
        p = stats.fisher_exact([[g1r1, g1r2], [g2r1, g2r2]])[1]
    
    return p

def dPrime(sPlusHitRate, falseAlarmRate):
    zHit = invNormApprox(sPlusHitRate)
    zFA = invNormApprox(falseAlarmRate)
    dPrime = zHit - zFA
    
    return dPrime

def criterion(sPlusHitRate, falseAlarmRate):
    zHit = invNormApprox(sPlusHitRate)
    zFA = invNormApprox(falseAlarmRate)
    c = -(zHit + zFA)/2
    return c

def invNormApprox(p):
    # InvNormApprox:  Pass the hit rate and false alarm rate, and this
    # routine returns zHit and zFa.  d' = zHit - zFa.
    # Converted from a basic routine provided by:
    # Brophy, A. L. (1986).  Alternatives to a table of criterion
    #  values in signal detection theory.  Behavior Research 
    #  Methods, Instruments, & Computers, 18, 285-286.
    #
    # Code adapted from http://memory.psych.mun.ca/models/dprime/

    sign = -1
    
    if p > 0.5:
        p = 1-p
        sign = 1
    
    if p < 0.00001:
        z = 4.3;
        return round(z*sign,3)
    
    r = math.sqrt(-math.log(p))
    
    z = (((2.321213*r+4.850141)*r-2.297965)*r-2.787189)/((1.637068*r+3.543889)*r+1)
    return round(z*sign,3)


if __name__ == '__main__':
    testSet = ((0.7778, 1-0.4404), (0.0, 1.0), (1.0, 1.0), (0.75, 0.3), (0.9, 0.3), (0.68, 0.09), (0.9, 0.5), (0.70, 0.30))
    
    print "\nTesting dPrime(hitRate, falseAlarmRate)\n"
    for test in testSet:
        print "dPrime(" + str(test[0]) + ", " + str(test[1]) + "): " + str(dPrime(test[0], test[1]))
    
    print "\nTesting Fisher Exact\n"
    print "Typical shrew results: " + str(fisherExact(12, 24, 5, 31, nTails=1))
    print "Wikipedia example: " + str(fisherExact(1, 11, 9, 3, nTails=1))
    
    
    nTrials = 100
    nWinsControl = 10
    for nWinsTest in range(15,25):
        res = round(fisherExact(nWinsControl, nTrials-nWinsControl, nWinsTest, nTrials-nWinsTest, nTails=2),3)
        print str(nWinsTest) + " / " + str(nTrials) + " vs 10% gives pValue of " + str(res)
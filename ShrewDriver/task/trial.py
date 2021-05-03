# Trial: trial.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

# Description: Contains all the info relevant to a trial, including results.
# Used by trial sequencer for randomization, and by UI to display results.
# Also used by the log analyzer.

from __future__ import division
import sys
sys.path.append("..")
from util.enumeration import *
from constants.task_constants import *


class Trial:
    
    def __init__(self):
        """Initialize the variables relevant to the Go/No Go task."""

        self.numSMinus = 0      # number of times SMINUS is presented
        
        self.trialStartTime = 0
        self.sMinusOrientation = '-1'   # degrees. -1 is a placeholder.
        self.sPlusOrientation = '-1'
        self.currentOri = '-1'  # placeholder until we know if it's an SMINUS or an SPLUS
        self.hint = False       # true if hint
        self.totalMicroliters = 0
        self.trialNum = 0
        self.ledPower = '-1'            # mW/mm^2, -1 is a placeholder
        
        # results
        self.result = Results.HIT
        self.resultState = States.REWARD
        self.hint = True
        
        self.stateHistory = []
        self.stateTimes = []
        self.actionHistory = []
        self.actionTimes = []

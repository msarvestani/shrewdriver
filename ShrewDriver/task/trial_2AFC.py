# Trial_2AFC: trial_2AFC.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

# Description: Contains all the info relevant to a trial, including results.
# Used by trial sequencer for randomization, and by UI to display results.
# Also used by the log analyzer.

from __future__ import division
import sys
sys.path.append("..")
from util.enumeration import *
from constants.task_constants_2AFC import *


class Trial_2AFC:
    
    def __init__(self):
        """Initialize the variables relevant to the 2AFC task."""

        self.numSMinus = 0          # number of times SMINUS is presented
        
        self.trialStartTime = 0
        self.sLeftOrientation = '-1'    # degrees. -1 is a placeholder.
        self.sRightOrientation = '-1'
        # placeholder until we know if it's an SMINUS or an SPLUS
        self.currentOri = '-1'
        self.hint = False           # true if hint
        self.totalMicrolitersLeft = 0
        self.totalMicrolitersRight = 0
        self.trialNum = 0
        self.ledPower = '-1'        # mW/mm^2, -1 is a placeholder
        
        # results
        self.result = Results.HIT_LEFT              # not sure what this is for
        self.resultState = States.REWARD_LEFT       # not sure what this is for
        self.hint = True
        
        self.stateHistory = []
        self.stateTimes = []
        self.actionHistory = []
        self.actionTimes = []

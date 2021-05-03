# SequencerStaircase: staircase.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import random
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer
from constants.task_constants import *


class SequencerStaircase(Sequencer):
    
    def __init__(self, trialSet):
        """
        Args:
            trialSet: [list] initial set of trials
        """

        self.minSMinus = trialSet[0].sMinusOrientation
        self.maxSMinus = trialSet[0].sMinusOrientation
        
        for trial in trialSet:
            if trial.sMinusOrientation < self.minSMinus:
                self.minSMinus = trial.sMinusOrientation
            if trial.sMinusOrientation > self.maxSMinus:
                self.minSMinus = trial.sMinusOrientation
        
        self.currentTrial = None
        
        # search parameters
        self.highEstimate = self.maxSMinus
        self.lowEstimate = self.minSMinus
        self.resolution = 0.5
        self.stepSize = (self.highEstimate-self.lowEstimate)/2
    
    def getNextTrial(self, trialResult):
        """
        So, we want to use the existing trial structure, with its same number
        of sMinus presentations and its sPlus orientation, but we're subbing
        in an sMinus orientation of our choice (according to the staircase).

        Args:
            trialResult: [int] result of the previous trial

        Returns: [int] A new trial if the previous trial was successful, the
                 current trial again if failed, and a randomly selected trial
                 from the trial set if the sequence is finished
        """

        newTrial = copy.copy(random.choice(self.trialSet))
        
        if self.currentTrial == None:
            self.currentTrial = random.choice(self.trialSet)
            return self.currentTrial
        else:
            if trialResult == Results.HIT or trialResult == Results.CORRECT_REJECT:
                # pick a new trial (possibly the same one again)
                self.currentTrial = random.choice(self.trialSet)
                return self.currentTrial
            else:
                # Failed, so repeat this trial
                return self.currentTrial

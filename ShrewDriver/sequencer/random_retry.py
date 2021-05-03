# SequencerRandomRetry: random_retry.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import sys
import random
sys.path.append("..")

from sequencer.sequencer_base import Sequencer
from constants.task_constants import *


class SequencerRandomRetry(Sequencer):
    
    def __init__(self, trialSet):
        """
        Args:
            trialSet: [list] Initial set of trials
        """

        self.trialSet = trialSet
        self.currentTrial = None
        
    def getNextTrial(self, trialResult):
        """
        If the most recent trial was not successful, repeat the trial.
        Otherwise, ranndomly select the next trial.

        Args:
            trialResult: [int] result of the most recent trial

        Returns: [int] the next trial
        """

        if self.currentTrial is None:
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
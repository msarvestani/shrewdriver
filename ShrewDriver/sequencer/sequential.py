# SequencerSequential: sequential.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer


class SequencerSequential(Sequencer):
    
    def __init__(self, trialSet):
        """
        Args:
            trialSet: [list] initial set of trials
        """
        self.trialSet = trialSet
        self.trialIndex = 0
        
    def getNextTrial(self, trialResult):
        """
        Grab next trial from the sequence.

        Args:
            result: [int] result of the previous trial

        Returns: [int] next trial
        """
        self.currentTrial = self.trialSet[self.trialIndex]
        self.trialIndex += 1
        if self.trialIndex > len(self.trialSet):
            self.trialIndex = 0
        return self.currentTrial

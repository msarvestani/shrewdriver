# SequencerRandom: random_seq.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import random
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer


class SequencerRandom(Sequencer):
    
    def __init__(self, trialSet):
        """
        Args:
            trialSet: [list] Initial set of trials
        """

        self.trialSet = trialSet
        
    def getNextTrial(self, trialResult):
        """
        Randomly selects the next trial

        Args:
            trialResult: [int] result of previous trial

        Returns: [int] randomly selected new trial
        """

        self.currentTrial = random.choice(self.trialSet)
        return self.currentTrial


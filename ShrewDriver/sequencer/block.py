# SequencerBlock: block.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import random
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer


class SequencerBlock(Sequencer):
    """The most basic block type for trial sequences."""

    def __init__(self, trialSet):
        """
        Sets up initial block and resets sequence.

        Args:
            trialSet: Initial set of trials
        """

        self.trialSet = trialSet
        self.resetBlock()
        
    def resetBlock(self):
        """Restarts the block."""
        self.block = []
        self.block.extend(self.trialSet)
        
    def getNextTrial(self, trialResult):
        """
        Args:
            trialResult: Result of the previous trial. Tells the sequencer how
                         to proceed.

        Returns: The next trial, randomly selected.
        """

        if len(self.block) == 0:
            self.resetBlock()
        return self.block.pop(random.randint(0, len(self.block)-1))

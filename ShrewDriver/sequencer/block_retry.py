# SequencerBlockRetry: block_retry.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import random
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer
from constants.task_constants import *


class SequencerBlockRetry(Sequencer):
    """This block type has the animal redo trials that it answers incorrectly"""

    def __init__(self, trialSet):
        """
        Sets up initial block and resets sequence.

        Args:
            trialSet: Initial set of trials
        """

        self.trialSet = trialSet
        self.resetBlock()
        self.currentTrial = None
        
    def resetBlock(self):
        """Restarts the block."""

        self.block = []
        self.block.extend(self.trialSet)
        
    def getNextTrial(self, trialResult):
        """
        Resets the block if a block has been successfully completed. If the
        trial result is a hit or correct reject, the sequence moves to the next
        trial, otherwise it repeats the trial.

        Args:
            trialResult: Result of the previous trial. Tells the sequencer how
                         to proceed.

        Returns: The next trial
        """

        if len(self.block) == 0:
            self.resetBlock()
        if trialResult == Results.HIT or trialResult == Results.CORRECT_REJECT \
                or self.currentTrial == None:
            self.currentTrial = self.block.pop(random.randint(0, len(self.block)-1))
            return self.currentTrial
        else:
            return self.currentTrial

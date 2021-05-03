# SequencerOptoBlock: opto_block.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 26 July 2018, JWS

from __future__ import division
import random
import sys

sys.path.append("..")
from sequencer.sequencer_base import Sequencer
from constants.task_constants import *


class SequencerOptoBlock(Sequencer):
    """This block type has the animal redo trials that it answers incorrectly"""

    def __init__(self, ledSet):
        """
        Sets up initial block and resets sequence.

        Args:
            trialSet: Initial set of trials
        """

        self.ledSet = ledSet
        self.resetBlock()
        self.currentPower = None

    def resetBlock(self):
        """Restarts the block."""

        self.ledBlock = []
        self.ledBlock.extend(self.ledSet)

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
        print ('upcoming led powers')
        print str(self.ledBlock)
        if len(self.ledBlock) == 0:
            self.resetBlock()
        if trialResult == Results.HIT or trialResult == Results.CORRECT_REJECT \
                or trialResult == Results.FALSE_ALARM or trialResult == Results.MISS \
                or self.currentPower == None:
            #self.currentPower = self.ledBlock.pop(random.randint(0, len(self.ledBlock) - 1))
            self.currentPower = self.ledBlock.pop(0)
            return self.currentPower
        else:
            return self.currentPower

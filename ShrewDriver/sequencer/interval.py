# SequencerInterval: interval.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12 March 2018

from __future__ import division
import random
import sys
sys.path.append("..")
from sequencer.sequencer_base import Sequencer

# interval sequencing:
# Shrew gets a set of easy S- orientations, then a set of hard ones, and repeat.
# This takes a few calls to set up. First, call init(), then set numEasy,
# numHard, and tell it what the easyOris and hardOris are.


class SequencerInterval(Sequencer):
    
    def __init__(self, trialSet):
        """
        Sets up initial block and resets sequence. Creates a dictionary of trials
        arranged by their orientation.

        Args:
            trialSet: [list] Initial set of trials
        """

        self.trialSet = trialSet
        self.easyOris = []
        self.hardOris = []
        self.numEasy = 30
        self.numHard = 20
        self.trialBuffer = []
        self.trialBufferPos = 0
        
        self.trialsByOrientation = {}
        
        for t in trialSet:
            ori = t.sMinusOrientation
            if not ori in self.trialsByOrientation.keys():
                self.trialsByOrientation[ori] = []
            self.trialsByOrientation[ori].append(t)

    def makeTrialBuffer(self):
        """
        Returns: [list] upcoming trials arranged by easy and hard S- orientations
        """

        self.trialBuffer = []
        for i in range(0, self.numEasy):
            ori = random.choice(self.easyOris)
            t = random.choice(self.trialsByOrientation[ori])
            self.trialBuffer.append(t)
        
        for i in range(0, self.numHard):
            ori = random.choice(self.hardOris)
            t = random.choice(self.trialsByOrientation[ori])
            self.trialBuffer.append(t)
        
    def getNextTrial(self, trialResult):
        """
        Args:
            trialResult: [int] result of the previous trial

        Returns: the next trial in the sequence, unless the sequence is done,
                 in that case, reset the buffer
        """

        if self.trialBufferPos == len(self.trialBuffer):
            # randomize trial buffer and reset index
            self.makeTrialBuffer()
            self.trialBufferPos = 0             
            
        t = self.trialBuffer[self.trialBufferPos]
        self.trialBufferPos += 1
        return t

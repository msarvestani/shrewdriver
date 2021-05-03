from __future__ import division

import sys
sys.path.append("..")

from constants.task_constants import *

"""
Fun things you can do with task parameters:

Suppose you want to change the balance of S+ and S- trials.
By default, it's 50/50, since sMinusPresentations = [0,1].
If you wanted it to be, say, 75% S+ trials, you can set:
sMinusPresentations = [0, 0, 0, 1].

Bear in mind that, if the sequence type is a _RETRY, you may get several copies
of a rare trial in a row.

Now, suppose you set:
sMinusPresentations = [0,1]
sPlusOrientations = [0, 45]
sMinusOrientations = [100, 110, 120]
Each trial would have a 50% chance of being an S+ or an S-.
The S- trials could be any of [100, 110, 120], while the S+ trials could show either 0 or 45.
"""

def load_parameters(task):
    print "Using settings for Baby!"

    task.showInteractUI = True  # Enables the interact UI, used in headfixed training.

    # Stim and task params
    task.sPlusOrientations = [90]
    task.sMinusOrientations = [102.5,110,135] #, 75,120] # [40]
    task.sMinusPresentations = [0,1,1,1] #how many times to display the SMINUS
    task.guaranteedSPlus = True #is there always an SPLUS in the trial?
    task.sequenceType = Sequences.RANDOM
    task.initiation = Initiation.LICK
    task.airPuffMode = AirPuffMode.NONE #AirPuffMode.BAD_DISCRIM #AirPuffMode.FALSE_ALARM_LICK #AirPuffMode.NONE

    # State durations
    task.timeoutFail = 3
    task.timeoutAbort = 3
    task.timeoutSuccess = 1
    task.timeoutNoResponse = 3
    task.timeoutCorrectReject = 1  # applies only when guaranteedSPlus is false
    task.initTime = 1

    task.variableDelayMin = 3.0
    task.variableDelayMax = 3.5

    task.gratingDuration = 1.0
    task.grayDuration = 1.5
    task.rewardPeriod = task.grayDuration  # needs to be no longer than gray duration!

    # Rewards / Hints
    task.rewardBolus = 70  # Microliters
    task.rewardBolusHardTrial = 100  # Microliters
    task.hintBolus = 30  # Microliters

    task.hintChance = .25  # chance of sending a low reward at the start of the reward period

    #stimbot setup, including command strings for each state
    #note that grating states will have an extra command added later to specify orientation and phase.
    task.screenDistanceMillis = 25
    task.commandStrings[States.TIMEOUT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.INIT] = 'ac paw px0 py0 sx12 sy12\n'
    task.commandStrings[States.DELAY] = 'sx0 sy0\n'
    task.commandStrings[States.SMINUS] = 'as sf0.25 tf0 jf0 ja0 gc1 px0 py0 sx999 sy999\n'
    task.commandStrings[States.GRAY] = 'sx0 sy0\n'
    task.commandStrings[States.SPLUS] = 'as sf0.25 tf0 jf0 ja0 gc1 px0 py0 sx999 sy999\n'
    task.commandStrings[States.REWARD] = 'sx0 sy0\n'


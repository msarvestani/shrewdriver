from __future__ import division
from __future__ import division
from random import randint

import sys
sys.path.append("..")

from constants.task_constants_2AFC import *

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
    print "Using settings for Chico-2AFC!"

    task.showInteractUI = True  # Enables the interact UI, used in headfixed training.

    # Stim and task params
    task.boundary = 60     #random int in [45-135]
    #task.boundary = randint(45,135)     #random int in [45-135]
    task.deviations = [2.5,5,10,22.5,45]
    task.sLeftOrientations = [task.boundary-x for x in task.deviations]
    task.sRightOrientations = [task.boundary+x for x in task.deviations]

    task.sLeftPresentations = [0,1] #how many times to display the SMINUS
    task.sequenceType = Sequences.RANDOM
    task.initiation = Initiation.LICK
    task.airPuffMode = AirPuffMode.NONE

    # State durations
    task.timeoutFail = 1
    task.timeoutAbort = 1
    task.timeoutSuccess = 1
    task.timeoutNoResponse = 1
    task.timeoutWrongLick = 1  # applies only when guaranteedSPlus is false
    task.initTime = 1

    task.variableDelayMin = 1.0
    task.variableDelayMax = 1.5

    task.gratingDuration = 1
    task.grayDuration = 1.5
    task.rewardPeriod = task.grayDuration  # needs to be no longer than gray duration!

    # Rewards / Hints
    task.rewardBolus = 80  # Microliters
    task.rewardBolusHardTrial = 100  # Microliters
    task.hintBolus = 30  # Microliters

    task.hintChance = 0  # chance of sending a low reward at the start of the reward perwn.

    #stimbot setup, including command strings for each state
    #note that grating states will have an extra command added later to specify orientation and phase.
    task.screenDistanceMillis = 25
    task.commandStrings[States.TIMEOUT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.TIMEOUT_LEFT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.TIMEOUT_RIGHT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.INIT] = 'ac paw px0 py0 sx12 sy12\n'
    task.commandStrings[States.DELAY] = 'sx0 sy0\n'
    task.commandStrings[States.SLEFT] = 'as sf0.25 tf0 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    task.commandStrings[States.SRIGHT] = 'as sf0.25 tf0 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    task.commandStrings[States.REWARD_LEFT] = 'sx0 sy0\n'
    task.commandStrings[States.REWARD_RIGHT] = 'sx0 sy0\n'



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
    print "Using settings for Pippin-2AFC!"

    task.showInteractUI = True  # Enables the interact UI, used in headfixed training.
    # Choose whether a psychopy-generated grating stim or a stim saved as a movie is used
    task.useMovie = False#True

    #task.sPlusDir = 'Phase2_ObjStims/Fig_left/Left_Movie_'
    #task.sMinusDir = 'Phase2_ObjStims/Fig_right/Right_Movie_'
    #task.sPlusDir = 'Phase3_ObjStims_Distractors/Fig_left/Left_Movie_'
    #task.sMinusDir = 'Phase3_ObjStims_Distractors/Fig_right/Right_Movie_'
    task.sPlusDir = 'version8/Fig_left/Left_Movie_'
    task.sMinusDir = 'version8/Fig_right/Right_Movie_'

    # Stim and task params
    task.boundary = int(180)  # int(90)
    task.deviations = [45, 90, 135]  # [5,10,22.5,45]
    if not task.useMovie:
        task.sLeftOrientations = [task.boundary - x for x in task.deviations]
        task.sRightOrientations = [task.boundary + x for x in task.deviations]
    else:
        # Here we list the movie file numbers. These are only used if task.useMovie is True
        task.sLeftOrientations = [1, 2, 3, 4]
        task.sRightOrientations = [1, 2, 3, 4]

    task.sLeftPresentations = [0,1]  # how many times to display the SMINUS
    task.sequenceType = Sequences.RANDOM_RETRY
    task.initiation = Initiation.LICK
    task.airPuffMode = AirPuffMode.NONE

    # State durations
    task.timeoutFail = 7
    task.timeoutAbort = 1
    task.timeoutSuccess = 1
    task.timeoutNoResponse = 1
    task.timeoutWrongLick = 1  # applies only when guaranteedSPlus is false
    task.timeoutCoolDown = 3

    if not task.useMovie:
        task.initTime = 1
        task.variableDelayMin = 1.0
        task.variableDelayMax = 1.5
        task.grayDuration = 2
    else:
        task.initTime = 1
        task.variableDelayMin = 0.75
        task.variableDelayMax = 1.25
        task.grayDuration = 1.5

    task.waitTime = 0
    task.gratingDuration = 1
    task.rewardPeriod = task.grayDuration  # needs to be no longer than gray duration!

    # Rewards / Hints
    task.rewardBolus = 30  # Microliters
    task.rewardBolusHardTrial = 30  # Microliters
    task.hintBolus = 20  # Microliters

    # chance of sending a low reward at the start of the reward period.
    task.hintChance = 0

    # stimbot setup, including command strings for each state
    # note that grating states will have an extra command added later to
    # specify orientation and phase.
    task.screenDistanceMillis = 25
    task.commandStrings[States.TIMEOUT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.TIMEOUT_LEFT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.TIMEOUT_RIGHT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.INIT] = 'ac paw px0 py0 sx12 sy12\n'
    task.commandStrings[States.DELAY] = 'sx0 sy0\n'
    # task.commandStrings[States.SLEFT] = 'as sf0.25 tf0 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    # task.commandStrings[States.SRIGHT] = 'as sf0.25 tf0 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    task.commandStrings[States.SLEFT] = 'as sf0.25 tf4 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    task.commandStrings[States.SRIGHT] = 'as sf0.25 tf4 gc0.9 jf0 ja0 px0 py0 sx999 sy999\n'
    task.commandStrings[States.REWARD_LEFT] = 'sx0 sy0\n'
    task.commandStrings[States.REWARD_RIGHT] = 'sx0 sy0\n'

    # ---------- Optogenetics Parameters ---------- #
    task.pulse_set = ['RAMP', 'SAWTOOTH', 'SINE_RAMP', 'SINE_TRAP', 'SQUARE', 'TRAP', 'TRIANGLE']
    task.pulses = Enumeration("Pulses", task.pulse_set)

    task.powerLevels = [0, 1, 4, 16]  # mW/mm2
    task.pulse_type = task.pulses.SQUARE

    # This will start/end the LED this many ms before/after the visual stim
    # set to zero if the LED should sync with the visual stim
    # Must be less than task.variableDelayMax
    task.rampDuration = 100  # msec.
    # This is typically this same as the visual stim.
    # HOWEVER, this is not true if using a pulse train
    task.sustainDuration = 5  # msec.
    # These parameters control pulse trains.
    # If you are using a pulse train, you MUST determine how to set the pulse duration
    # (ramps + sustain) and pulse ISI to completely cover the length of the visual stim + any flanks.
    # One cycle is defined as ramps + sustain + isi
    # Ex: 1000ms visual stim, want 10 Hz pulses of 5ms ON with 100ms flanks.
    # set rampDuration = 100, sustainDuration = 5, pulseISI = 95, numCycles = 12
    task.pulseTrain = 0  # Set to 1 if using pulse trains
    task.numCycles = 12
    task.pulseISI = 95  # msec.

    # we need to tell the opto process what the parameters for timing are
    # ramp times will be equal for rampUp and rampDown
    task.setup_cmd = 'cmd pls' + str(task.pulse_type) + ' ' \
                     + 'sus' + str(task.sustainDuration) + ' ' \
                     + 'rmp' + str(task.rampDuration) + ' ' \
                     + 'plstrn' + str(task.pulseTrain) + ' ' \
                     + 'numcycl' + str(task.numCycles) + ' ' \
                     + 'plsisi' + str(task.pulseISI) + '\n'

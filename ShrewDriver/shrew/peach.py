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
    print "Using settings for Peach!"

    task.showInteractUI = True  # Enables the interact UI, used in headfixed training.
    # Choose whether a psychopy-generated grating stim or a stim saved as a movie is used
    task.useMovie = False
    task.sPlusDir = 'FIG_Movies/FIG_Movie_'
    task.sMinusDir = 'BG_Movies/BG_Movie_'
    # Choose if optogenetic stimulation is used
    task.useOpto = False

    # Stim and task params
    task.sPlusOrientations = [0, 45, 90, 135]
    task.sMinusOrientations = [10] # [40]
    task.sMinusPresentations = [0] #how many times to display the SMINUS
    task.guaranteedSPlus = True #is there always an SPLUS in the trial?
    task.sequenceType = Sequences.RANDOM
    task.initiation = Initiation.LICK
    task.airPuffMode = AirPuffMode.NONE#FALSE_ALARM_LICK #AirPuffMode.BAD_DISCRIM #AirPuffMode.FALSE_ALARM_LICK #AirPuffMode.NONE

    # State durations
    task.timeoutFail = 3
    task.timeoutAbort = 3
    task.timeoutSuccess = 3
    task.timeoutNoResponse = 3
    task.timeoutCorrectReject = 1  # applies only when guaranteedSPlus is false
    task.initTime = 1

    task.variableDelayMin = 3.0
    task.variableDelayMax = 3.5

    task.gratingDuration = 0.5
    task.grayDuration = 1.5
    task.rewardPeriod = task.grayDuration  # needs to be no longer than gray duration!

    # Rewards / Hints
    task.rewardBolus = 70  # Microliters
    task.rewardBolusHardTrial = 110  # Microliters
    task.hintBolus = 30  # Microliters

    task.hintChance = .05# chance of sending a low reward at the start of the reward period

    #stimbot setup, including command strings for each state
    #note that grating states will have an extra command added later to specify orientation and phase.
    task.screenDistanceMillis = 32
    task.commandStrings[States.TIMEOUT] = 'ac pab px0 py0 sx12 sy12\n'
    task.commandStrings[States.INIT] = 'ac paw px0 py0 sx12 sy12\n'
    task.commandStrings[States.DELAY] = 'sx0 sy0\n'
    task.commandStrings[States.SMINUS] = 'as sf0.25 tf0 jf0 ja0.3 gc0.9 px0 py0 sx999 sy999\n'
    task.commandStrings[States.GRAY] = 'sx0 sy0\n'
    task.commandStrings[States.SPLUS] = 'as sf0.25 tf0 jf0 ja0.3 gc0.9 px0 py0 sx999 sy999\n'
    task.commandStrings[States.REWARD] = 'sx0 sy0\n'

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
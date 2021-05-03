# Task2AFC: task_2AFC.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

# Description: Prepares and monitors progress of steps in a two alternative
# forced choice task, including stimulus presentation, reward/punishment/hint
# delivery, logging, etc.

from __future__ import division
import fileinput
import re
import math
import random
import time
import itertools
import sys
sys.path.append("..")

from constants.task_constants_2AFC import *

from task_mixin_2AFC import TaskMixin_2AFC

from sequencer.sequencer_base import Sequencer
from trial_2AFC import Trial_2AFC


class Task2AFC(TaskMixin_2AFC):
    
    def __init__(self, training, shrewDriver):
        """
        Inherits class variables from ShrewDriver

        Args:
            shrewDriver: [object] the ShrewDriver object
        """

        self.training = training
        self.shrewDriver = shrewDriver
        self.animalName = self.shrewDriver.animalName

        # flag for potential optogenetics stuff
        self.useOpto = self.shrewDriver.useOpto
        self.useOptoFSOnly = self.shrewDriver.useOptoFSOnly
        self.optoNow = False

        self.replaceOrientation = ""
        self.make_stuff()

        if self.useOpto:
            self.training.optoController.write(self.setup_cmd)
        
    def prepare_trial(self):
        """Preps some settings for the upcoming trial and determine if the
        trial will be hinted."""

        # prepare to run trial
        self.sLeftDisplaysLeft = self.currentTrial.numSLeft
        self.currentTrial.totalMicrolitersLeft = 0
        self.currentTrial.totalMicrolitersRight = 0
        self.isHighRewardTrial = self.sLeftDisplaysLeft > min(self.sLeftPresentations)

        # Randomly generate a number to determine if a the trial will be hinted
        # See the shrew/----_2AFC.py for hint chance.
        if random.uniform(0, 1) < self.hintChance:
            self.doHint = True
        else:
            self.doHint = False
    
    def make_trial_set(self):
        """Creates a list of all possible combinations of SLeft and SRight
        orientations, checks that they are different, and adds them to the set
        of all possible trials. Then if the sequence type is interval or
        interval retry, the hard/easy orientations and the number of each is
        logged in the sequencer."""

        self.trialSet = []
        if self.useOpto!=1:
            all_pairs = list(itertools.product(self.sRightOrientations,
                                               self.sLeftOrientations))
        else:
            all_pairs = list(itertools.product(self.sRightOrientations,
                                               self.sLeftOrientations,
                                               self.powerLevels))

        for numSLeft in self.sLeftPresentations:
            for p in all_pairs:
                if self.useOpto:
                    (sRightOrientation, sLeftOrientation, ledPower) = p
                else:
                    (sRightOrientation, sLeftOrientation) = p

                if abs(sRightOrientation - sLeftOrientation) < 0.001:
                    # make sure SPLUS and SMINUS are different
                    continue
                
                t = Trial_2AFC()
                t.numSLeft = numSLeft
                t.sRightOrientation = sRightOrientation
                t.sLeftOrientation = sLeftOrientation

                # We only mess with the LED power if we're doing optogenetics,
                # otherwise the power level stays the same as the placeholder.
                if self.useOpto:
                    t.ledPower = ledPower

                self.trialSet.append(t)
        
        print str(len(self.trialSet)) + " different trial conditions."
        
        self.sequencer = Sequencer(self.trialSet, self.sequenceType)
        if self.sequenceType == Sequences.INTERVAL or self.sequenceType == Sequences.INTERVAL_RETRY:
            self.sequencer.sequencer.easyOris = self.easyOris
            self.sequencer.sequencer.hardOris = self.hardOris
            self.sequencer.sequencer.numEasy = self.numEasy
            self.sequencer.sequencer.numHard = self.numHard
        
    def start(self):
        """Starts the first trial."""

        self.stateDuration = self.initTime
        self.change_state(States.INIT)
    
    def check_state_progression(self):
        """Checks the current state and determines what do do next"""
        # Get current clock time
        now = time.time()

        if self.state == States.INIT:
            # Wait for the shrew to stop licking, unless its initiation type is
            # LICK. Note that the parentheses around the logic below are to
            # conform to the PEP8 style convention.
            if self.initiation != Initiation.LICK:
                if (self.isLeftLicking or self.isRightLicking or
                        self.isCenterLicking or
                        self.lastLeftLickAt > self.stateStartTime or
                        self.lastRightLickAt > self.stateStartTime or
                        self.lastCenterLickAt > self.stateStartTime):
                    self.stateStartTime = now
            
            # recompute state end time based on the above
            self.stateEndTime = self.stateStartTime + self.stateDuration
                
            # -- progression condition -- #
            doneWaiting = False
            if (self.initiation == Initiation.LICK and
                    self.lastCenterLickAt > self.stateStartTime and not
                    self.isCenterLicking):
                # Shrew is supposed to lick, and it has, but it's not licking
                # right now.
                if (now - self.lastCenterLickAt) > 0.5:
                    # In fact, it licked at least half a second ago, so it
                    # should REALLY not be licking now. Let's proceed with the
                    # trial.
                    doneWaiting = True

            if doneWaiting:
                self.stateDuration = random.uniform(self.variableDelayMin,
                                                    self.variableDelayMax)
                self.change_state(States.DELAY)
        
        if self.state == States.DELAY:
            # -- fail conditions -- #
            self.check_fail()

            # -- opto condition -- #
            if (now > self.stateEndTime - (self.rampDuration / 1000) and
                    self.useOpto and not
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration
                self.optoNow = True
                power = str(self.currentTrial.ledPower)
                opto_cmd = 'cmd pwr' + power
                self.training.optoController.write(opto_cmd)
                self.training.log_plot_and_analyze(opto_cmd, time.time())

            # -- progression condition -- #
            if now > self.stateEndTime:
                self.prepare_grating_state()

        if self.state == States.SLEFT:
            # -- fail conditions --#
            self.check_fail_left()

            # -- progression condition --#
            if now > self.stateEndTime:
                # Possibly dispense a small reward as a hint.
                if self.doHint:
                    self.training.dispense_hint_left(self.hintBolus / 1000)
                # go to reward state
                self.stateDuration = self.rewardPeriod
                self.change_state(States.REWARD_LEFT)

        if self.state == States.SRIGHT:
            # -- fail conditions -- #
            self.check_fail_right()
                
            # -- progression condition -- #
            if now > self.stateEndTime:

                # Possibly dispense a small reward as a hint.
                if self.doHint:
                    self.training.dispense_hint_right(self.hintBolus / 1000)

                # go to reward state 
                self.stateDuration = self.rewardPeriod
                self.change_state(States.REWARD_RIGHT)
                
        if self.state == States.REWARD_RIGHT:
            # -- opto condition -- #
            # This bit of the code catches us as we come out of the SPLUS
            if (now >= self.stateStartTime + (self.rampDuration / 1000) and
                    self.useOpto and
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration. The opto stim should have ended on its own
                # by now, so we reset the opto flag
                self.optoNow = False

            # -- success condition -- #
            if self.lastRightLickAt >= self.stateStartTime:
                if self.isHighRewardTrial:
                    self.training.dispense_reward_right(self.rewardBolusHardTrial / 1000)
                else:
                    self.training.dispense_reward_right(self.rewardBolus / 1000)
                
                self.stateDuration = self.timeoutSuccess
                self.trialResult = Results.HIT_RIGHT
                self.change_state(States.TIMEOUT_RIGHT)

            # -- bad-lick condition -- #
            if self.lastLeftLickAt >= self.stateStartTime:
                self.stateDuration = self.timeoutWrongLick
                self.trialResult = Results.MISS_RIGHT
                self.change_state(States.TIMEOUT_RIGHT)

            # -- progression condition -- #
            if now > self.stateEndTime:
                self.stateDuration = self.timeoutNoResponse
                self.trialResult = Results.NO_RESPONSE_RIGHT
                self.change_state(States.TIMEOUT_RIGHT)

        if self.state == States.REWARD_LEFT:
            # -- opto condition -- #
            # This bit of the code catches us as we come out of the SPLUS
            if (now >= self.stateStartTime + (self.rampDuration / 1000) and
                    self.useOpto and
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration. The opto stim should have ended on its own
                # by now, so we reset the opto flag
                self.optoNow = False

            # -- success condition --#
            if self.lastLeftLickAt >= self.stateStartTime:
                if self.isHighRewardTrial:
                    self.training.dispense_reward_left(self.rewardBolusHardTrial / 1000)
                else:
                    self.training.dispense_reward_left(self.rewardBolus / 1000)

                self.stateDuration = self.timeoutSuccess
                self.trialResult = Results.HIT_LEFT
                self.change_state(States.TIMEOUT_LEFT)

            # -- bad-lick condition -- #
            if self.lastRightLickAt >= self.stateStartTime:
                self.stateDuration = self.timeoutWrongLick
                self.trialResult = Results.MISS_LEFT
                self.change_state(States.TIMEOUT_LEFT)

            # -- progression condition --#
            if now > self.stateEndTime:
                self.stateDuration = self.timeoutNoResponse
                self.trialResult = Results.NO_RESPONSE_LEFT
                self.change_state(States.TIMEOUT_LEFT)
                
        if (self.state == States.TIMEOUT or
                self.state == States.TIMEOUT_RIGHT or
                self.state == States.TIMEOUT_LEFT):

            # kill the optogenetics stim, if necessary
            if self.useOpto:
                self.training.optoController.write('reset0')

            # -- progression condition -- #
            if self.initiation == Initiation.TAP_ONSET:
                if not self.isTapping and now > self.stateEndTime:
                    self.stateDuration = self.initTime
                    self.change_state(States.INIT)
            else:
                if now > self.stateEndTime:
                    self.stateDuration = self.initTime
                    self.change_state(States.INIT)

    def change_state(self, newState):
        """
        Changes the state progression to the new state and logs the change. If
        the new state is any kind of timeout, it resets trial parameters for a
        new trial.

        Args:
            newState: [int] the new state to be presented
        """

        # runs every time a state changes
        # be sure to update self.stateDuration BEFORE calling this
        self.oldState = self.state
        self.state = newState
        self.stateStartTime = time.time()
        
        self.training.log_plot_and_analyze("State" + str(self.state), time.time())

        # if changed to timeout, reset trial params for the new trial
        if (newState == States.TIMEOUT or newState == States.TIMEOUT_RIGHT or
                newState == States.TIMEOUT_LEFT):
            # tell UI about the trial that just finished
            print Results.whatis(self.trialResult) + "\n"
            self.shrewDriver.sigTrialEnd.emit()
            
            # prepare next trial
            self.currentTrial = self.sequencer.getNextTrial(self.trialResult)
            self.prepare_trial()
            self.trialNum += 1
            print("\nTrial "+str(self.trialNum)+"\n")
        
        # update screen
        if self.stateDuration > 0:

            if newState == States.SLEFT or newState == States.SRIGHT:
                # it's a grating, so call the base grating command
                # and add the orientation and phase

                if self.useMovie:
                    # Here we're co-opting the grating commands to show a movie
                    # instead
                    if newState == States.SLEFT:
                        mov = str(self.currentTrial.sLeftOrientation)
                        mov_path = "movSP" + mov

                    elif newState == States.SRIGHT:
                        mov = str(self.currentTrial.sRightOrientation)
                        mov_path = "movSM" + mov

                    self.training.stimDevice.write(str(self.state) + " " +
                                                   mov_path + "\n")
                    self.training.log_plot_and_analyze(mov_path, time.time())

                else:
                    ori = ""
                    if self.replaceOrientation != "":
                        # If commanded by the UI to swap in a different ori,
                        # do so.
                        ori = self.replaceOrientation
                        self.replaceOrientation = ""
                    elif newState == States.SLEFT:
                        ori = str(self.currentTrial.sLeftOrientation)
                    elif newState == States.SRIGHT:
                        ori = str(self.currentTrial.sRightOrientation)

                    phase = str(round(random.random(), 2))
                    oriPhase = oriPhase = "sqr" + ori + " ph" + phase

                    self.training.stimDevice.write(str(self.state) + " " +
                                                   oriPhase + "\n")
                    self.training.log_plot_and_analyze(oriPhase, time.time())

            else:
                self.training.stimDevice.write(str(self.state) + "\n")

        # let Spike2 know which state we are now in
        self.training.daq.send_stimcode(StateStimcodes[newState])

        # update end time
        self.stateEndTime = self.stateStartTime + self.stateDuration

        # print, just in case.
        msg = 'state changed to ' + str(States.whatis(newState)) + \
              ' duration ' + str(self.stateDuration)

        if str(States.whatis(newState)) == 'SRIGHT':
            msg += ' orientation ' + str(self.currentTrial.sRightOrientation)
        if str(States.whatis(newState)) == 'SLEFT':
            msg += ' orientation ' + str(self.currentTrial.sLeftOrientation)
        # print msg

    def check_fail(self):
        """Checks to see if the animal failed the trial at any port."""
        # Checks if shrew licks when it shouldn't.
        if (self.isLeftLicking or self.isRightLicking or
                self.lastLeftLickAt > self.stateStartTime or
                self.lastRightLickAt > self.stateStartTime):
            # any other time, licks are bad m'kay
            self.fail()

    def check_fail_left(self):
        """Checks to see if the user failed the trial at the left port."""

        # Checks if shrew licks when it shouldn't.
        if (self.isLeftLicking or self.isRightLicking or
                self.lastLeftLickAt > self.stateStartTime or
                self.lastRightLickAt > self.stateStartTime):
            # any other time, licks are bad m'kay
            self.fail_left()

    def check_fail_right(self):
        """Checks to see if the user failed the trial at the right port."""

        # Checks if shrew licks when it shouldn't.
        if (self.isLeftLicking or self.isRightLicking or
                self.lastLeftLickAt>self.stateStartTime or
                self.lastRightLickAt > self.stateStartTime):
            # any other time, licks are bad m'kay
            self.fail_right()

    def fail(self):
        """Changes state to TASK_FAIL and delivers punishment if necessary."""

        self.stateDuration = self.timeoutFail
        self.trialResult = Results.TASK_FAIL

        if (self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or
                self.airPuffMode == AirPuffMode.BAD_LICK):
            self.training.airPuff.puff()
            self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
            self.training.log_plot_and_analyze("Puff", time.time())

        self.change_state(States.TIMEOUT)
    
    def fail_right(self):
        """Changes state to TASK_FAIL and delivers punishment if necessary.
        Follows a call to self.check_fail_right()."""

        self.stateDuration = self.timeoutFail
        self.trialResult = Results.TASK_FAIL_RIGHT

        if (self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or
                self.airPuffMode == AirPuffMode.BAD_LICK):
            self.training.airPuff.puff()
            self.training.daq.send_stimcode(STIMCODE_FAIL_PUFF)
            self.training.log_plot_and_analyze("Puff", time.time())

        self.change_state(States.TIMEOUT_RIGHT)

    def fail_left(self):
        """Changes state to TASK_FAIL and delivers punishment if necessary.
            Follows a call to self.check_fail_left()."""

        self.stateDuration = self.timeoutFail
        self.trialResult = Results.TASK_FAIL_LEFT

        if (self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or
                self.airPuffMode == AirPuffMode.BAD_LICK):
            self.training.airPuff.puff()
            self.training.daq.send_stimcode(STIMCODE_FAIL_PUFF)
            self.training.log_plot_and_analyze("Puff", time.time())

        self.change_state(States.TIMEOUT_LEFT)

    def abort(self):
        """Aborts trial based on user fail."""

        self.stateDuration = self.timeoutAbort
        self.trialResult = Results.ABORT
        self.change_state(States.TIMEOUT)
    
    def prepare_grating_state(self):
        """Prepares the next grating based on the number of remaining SLeft or
        SRight stims."""

        # goes to either SLeft or SRight.
        # this has its own function because it's called from both DELAY and GRAY.
        if self.sLeftDisplaysLeft > 0:
            self.stateDuration = self.gratingDuration
            self.change_state(States.SLEFT)
            self.sLeftDisplaysLeft -= 1

        else:
            # finished all SLeft displays
            if (self.currentTrial.numSLeft < max(self.sLeftPresentations) or
                    max(self.sLeftPresentations) == 0):

                # continue to SPLUS
                self.stateDuration = self.gratingDuration
                self.change_state(States.SRIGHT)

    # --- Interactive UI commands --- #
    def ui_start_trial(self):
        """Start a trial when user presses the button on the UI."""

        if (self.state == States.TIMEOUT or
                self.state == States.TIMEOUT_LEFT or
                States.TIMEOUT_RIGHT or
                self.state == States.INIT):
            self.training.log_plot_and_analyze("User started trial", time.time())
            print "User started trial"
            self.stateDuration = random.uniform(self.variableDelayMin,
                                                self.variableDelayMax)
            self.training.daq.send_stimcode(STIMCODE_USER_TRIAL)
            time.sleep(0.001)
            self.change_state(States.DELAY)

    def ui_fail_task(self):
        """Fail a trial when user presses the button on the UI."""
        self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
        self.training.log_plot_and_analyze("Trial failed at user's request",
                                           time.time())
        print "Trial failed at user's request"
        self.fail()


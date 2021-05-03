# Task2AFCOpenEnd: task_2AFC_OpenEnd.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

# This version differs from the standard 2AFC by having an infinitely
# looping movie stimulus and an infinite response period. The shrew can
# respond at any time during the stimulus display period. This script
# ignores the task grating duration set in the animal settings file.

from __future__ import division
import sys
import fileinput
import re
import math
import random
import time
import itertools

sys.path.append("..")

from constants.task_constants_2AFC import *

from task_mixin_2AFC import TaskMixin_2AFC

from sequencer.sequencer_base import Sequencer
from trial_2AFC import Trial_2AFC


class Task2AFCOpenEnd(TaskMixin_2AFC):

    def __init__(self, training, shrewDriver):
        """
        Inherits class variables from ShrewDriver

        Args:
            shrewDriver: [object] the ShrewDriver object
        """

        self.training = training
        self.shrewDriver = shrewDriver
        self.animalName = self.shrewDriver.animalName

        self.replaceOrientation = ""
        self.make_stuff()

    def prepare_trial(self):
        """Preps some settings for the upcoming trial and determine if the
        trial will be hinted."""

        # prepare to run trial
        self.sLeftDisplaysLeft = self.currentTrial.numSLeft
        self.currentTrial.totalMicrolitersLeft = 0
        self.currentTrial.totalMicrolitersRight = 0
        self.isHighRewardTrial = self.sLeftDisplaysLeft > min(self.sLeftPresentations)

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
        all_pairs = list(itertools.product(self.sRightOrientations, self.sLeftOrientations))
        for numSLeft in self.sLeftPresentations:
            for p in all_pairs:
                (sRightOrientation, sLeftOrientation) = p
                if abs(sRightOrientation - sLeftOrientation) < 0.001:
                    # make sure SPLUS and SMINUS are different
                    continue

                t = Trial_2AFC()
                t.numSLeft = numSLeft
                t.sRightOrientation = sRightOrientation
                t.sLeftOrientation = sLeftOrientation

                self.trialSet.append(t)

        print str(len(self.trialSet)) + " different trial conditions."

        self.sequencer = Sequencer(self.trialSet, self.sequenceType)
        if (self.sequenceType == Sequences.INTERVAL or
                self.sequenceType == Sequences.INTERVAL_RETRY):
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

        # Keep tabs on the current time.
        now = time.time()

        if self.state == States.INIT:
            doneWaiting = False

            # Wait for the shrew to stop licking, unless its init type is LICK
            if self.initiation != Initiation.LICK:

                # if this is the auto-initiation, simply progress from here
                if self.initiation == Initiation.AUTO:
                    self.stateStartTime = now
                    doneWaiting = True

                if (self.isLeftLicking or self.isRightLicking or
                        self.isCenterLicking or
                        self.lastLeftLickAt > self.stateStartTime or
                        self.lastRightLickAt > self.stateStartTime or
                        self.lastCenterLickAt > self.stateStartTime):
                    self.stateStartTime = now

            # recompute state end time based on the above
            self.stateEndTime = self.stateStartTime + self.stateDuration

            # -- progression condition --#
            if (self.initiation == Initiation.LICK and
                    self.lastCenterLickAt > self.stateStartTime and not
                    self.isCenterLicking):
                # Shrew is supposed to lick, and it has,
                # but it's not licking right now.
                if (now - self.lastCenterLickAt) > 0.5:
                    # In fact, it licked at least half a second ago, so it
                    # should REALLY not be licking now. Let's proceed.
                    doneWaiting = True

            if doneWaiting:
                # In the Open Ended task, this should be instantaneous.
                # Progress directly to the stim
                self.prepare_grating_state()

        if self.state == States.SLEFT:
            # The SLEFT and SRIGHT flags are now a never ending reward period

            # -- hint -- #
            # We put the hint at the beginning of hinted trials
            # of the stim
            if self.doHint:
                self.training.dispense_hint_left(self.hintBolus / 1000)
                # Reset hint
                self.doHint = False

            # -- fail conditions --#
            # We will first check to see if the animal timed the trial out.
            self.check_fail_left()

            # -- progression condition --#
            if self.check_progress_left():
                # go to reward state
                self.stateDuration = self.rewardPeriod
                self.change_state(States.REWARD_LEFT)

        if self.state == States.SRIGHT:
            # The SLEFT and SRIGHT flags are technically now a never ending
            # reward period

            # -- hint -- #
            # If this is a hinted trial, the hint comes at the beginning.
            if self.doHint:
                self.training.dispense_hint_right(self.hintBolus / 1000)
                # Reset hint
                self.doHint = False

            # -- fail conditions -- #
            # We will first check to see if the animal timed the trial out.
            self.check_fail_right()

            # -- progression condition -- #
            if self.check_progress_right():
                # go to reward state
                self.stateDuration = self.rewardPeriod
                self.change_state(States.REWARD_RIGHT)

        if self.state == States.REWARD_RIGHT:
            # The modified reward period simply distributes the reward. There
            # is no bad lick or timeout. This state simply is used to say
            # that a reward was dispensed to the right syringe.
            # -- success condition -- #
            self.training.dispense_reward_right(self.rewardBolus / 1000)

            self.stateDuration = self.timeoutSuccess
            self.trialResult = Results.HIT_RIGHT
            self.change_state(States.TIMEOUT_RIGHT)

        if self.state == States.REWARD_LEFT:
            # The modified reward period simply distributes the reward. There
            # is no bad lick or timeout. This state simply is used to say
            # that a reward was dispensed to the right syringe.
            # -- success condition --#
            self.training.dispense_reward_left(self.rewardBolus / 1000)

            self.stateDuration = self.timeoutSuccess
            self.trialResult = Results.HIT_LEFT
            self.change_state(States.TIMEOUT_LEFT)

        if (self.state == States.TIMEOUT or
                self.state == States.TIMEOUT_RIGHT or
                self.state == States.TIMEOUT_LEFT):

            # -- progression condition -- #
            if self.initiation == Initiation.TAP_ONSET:
                if not self.isTapping and now > self.stateEndTime:
                    self.stateDuration = self.initTime
                    self.change_state(States.INIT)
            else:
                doneWaiting = False
                if (now > self.stateEndTime and not
                    self.isRightLicking and not self.isLeftLicking):
                    # Enforce a minimum timeout period where the shrew is
                    # not licking a spout.
                    if (now - self.lastLeftLickAt) > self.timeoutCoolDown and \
                            (now - self.lastRightLickAt) > self.timeoutCoolDown:
                        # In fact, it licked at least half a second ago, so it
                        # should REALLY not be licking now. Let's proceed.
                        doneWaiting = True

                if doneWaiting:
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
        if (newState == States.TIMEOUT or
                newState == States.TIMEOUT_RIGHT or
                newState == States.TIMEOUT_LEFT):
            # tell UI about the trial that just finished
            print Results.whatis(self.trialResult) + "\n"
            self.shrewDriver.sigTrialEnd.emit()

            # prepare next trial
            self.currentTrial = self.sequencer.getNextTrial(self.trialResult)
            self.prepare_trial()
            self.trialNum += 1
            print("\nTrial " + str(self.trialNum) + "\n")

        # update screen
        if self.stateDuration > 0:

            if newState == States.SLEFT or newState == States.SRIGHT:
                # it's a grating, so call the base grating command
                # and add the orientation and phase

                if self.useMovie:
                    # Here we're using the stim commands to show a movie
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

        # Checks if shrew licks the wrong side.
        if self.isRightLicking or self.lastRightLickAt > self.stateStartTime:
            self.fail_left()

    def check_fail_right(self):
        """Checks to see if the user failed the trial at the right port."""

        # Checks if shrew licks the wrong side.
        if self.isLeftLicking or self.lastLeftLickAt > self.stateStartTime:
            self.fail_right()

    def check_progress_left(self):
        """Checks if the shrew licked for the correct side to move to reward
        period"""

        if self.isLeftLicking or self.lastLeftLickAt > self.stateStartTime:
            return True
        else:
            return False

    def check_progress_right(self):
        """Checks if the shrew licked for the correct side to move to reward
        period"""

        # Checks if the shrew licked for the correct side to move to reward period
        if self.isRightLicking or self.lastRightLickAt > self.stateStartTime:
            return True
        else:
            return False

    def fail(self):
        """Changes state to TASK_FAIL and delivers punishment if necessary."""

        self.stateDuration = self.timeoutFail
        self.trialResult = Results.TASK_FAIL

        if self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or \
                self.airPuffMode == AirPuffMode.BAD_LICK:
            self.training.airPuff.puff()
            self.training.log_plot_and_analyze("Puff", time.time())

        self.change_state(States.TIMEOUT)

    def fail_right(self):
        """Changes state to MISS_RIGHT and delivers punishment if necessary."""

        # In the open-ended 2AFC task, there is no task failure, only misses
        self.stateDuration = self.timeoutFail
        self.trialResult = Results.MISS_RIGHT

        if self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or \
                self.airPuffMode == AirPuffMode.BAD_LICK:
            self.training.airPuff.puff()
            self.training.log_plot_and_analyze("Puff", time.time())

        self.change_state(States.TIMEOUT_RIGHT)

    def fail_left(self):
        """Changes state to MISS_LEFT and delivers punishment if necessary."""

        # In the open-ended 2AFC task, there is no task failure, only misses
        self.stateDuration = self.timeoutFail
        self.trialResult = Results.MISS_LEFT

        if self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or \
                self.airPuffMode == AirPuffMode.BAD_LICK:
            self.training.airPuff.puff()
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
        if self.sLeftDisplaysLeft > 0:
            self.stateDuration = self.gratingDuration
            self.change_state(States.SLEFT)
            self.sLeftDisplaysLeft -= 1
        else:
            # finished all SLeft displays
            if self.currentTrial.numSLeft < max(self.sLeftPresentations) or \
                    max(self.sLeftPresentations) == 0:
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
            self.training.log_plot_and_analyze("User started trial",
                                               time.time())
            print "User started trial"
            # Again, this changes to go directly to a movie for open ended 2AFC
            self.training.daq.send_stimcode(STIMCODE_USER_TRIAL)
            self.prepare_grating_state()

    def ui_fail_task(self):
        """Fail a trial when user presses the button on the UI."""

        self.training.log_plot_and_analyze("Trial failed at user's request",
                                           time.time())
        print "Trial failed at user's request"
        self.fail()


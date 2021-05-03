# TaskGNG: task_gonogo.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

from __future__ import division
import sys
import fileinput
import re
import math
import random
import time
import itertools
from trial import Trial
from task_mixin import TaskMixin

sys.path.append("..")

from constants.task_constants import *
from sequencer.sequencer_base import Sequencer


class TaskGNG_LA(TaskMixin):

    def __init__(self, training, shrewDriver):
        """
        Args:
            training: [object] training object from task/training.py
            shrewDriver: [object] ShrewDriver object from shrewdriver.py
        """

        self.training = training
        self.shrewDriver = shrewDriver
        self.animalName = self.shrewDriver.animalName

        # flag for potential optogenetics stuff
        self.useOpto = self.shrewDriver.useOpto
        self.useOptoFSOnly = self.shrewDriver.useOptoFSOnly
        self.optoNow = False
        self.optoStim2 = False

        self.replaceOrientation = ""
        self.make_stuff()

        if self.useOpto:
            self.training.optoController.write(self.setup_cmd)

    def prepare_trial(self):
        """Preps some settings for the upcoming trial and determine if the
        trial will be hinted."""

        # prepare to run trial
        self.sMinusDisplaysLeft = self.currentTrial.numSMinus
        self.currentTrial.totalMicroliters = 0
        self.isHighRewardTrial = self.sMinusDisplaysLeft > min(self.sMinusPresentations)
        if random.uniform(0, 1) < self.hintChance:
            self.doHint = True
        else:
            self.doHint = False

    def make_trial_set(self):
        """Creates a list of all possible combinations of S- and S+
        orientations, checks that they are different, and adds them to the set
        of all possible trials. Then if the sequence type is interval or
        interval retry, the hard/easy orientations and the number of each is
        logged in the sequencer."""

        self.trialSet = []

        # This is where we add the potential optogenetics stuff. We create a
        # trial set including all possible combinations of SPLUS and SMINUS
        # stims, and if specified, LED powers.
        if self.useOpto:
            all_sets = list(itertools.product(self.sPlusOrientations,
                                              self.sMinusOrientations,
                                              self.powerLevels))
        else:
            all_sets = list(itertools.product(self.sPlusOrientations,
                                              self.sMinusOrientations))

        for numSMinus in self.sMinusPresentations:
            for p in all_sets:
                if not self.useOpto:
                    (sPlusOrientation, sMinusOrientation) = p
                else:
                    (sPlusOrientation, sMinusOrientation, ledPower) = p

                if self.useMovie:
                    # If we're using a movie then we can have the same movie
                    # index available because it will be in a different folder.
                    # Edited for Doris Tsao task - MM 2017/12/11
                    pass
                else:
                    if abs(sPlusOrientation - sMinusOrientation) < 0.001:
                        # make sure SPLUS and SMINUS are different
                        continue

                t = Trial()
                t.numSMinus = numSMinus
                t.sPlusOrientation = sPlusOrientation
                t.sMinusOrientation = sMinusOrientation

                # We only mess with the LED power if we're doing optogenetics,
                # otherwise the power level stays the same as the placeholder.
                if self.useOpto:
                    t.ledPower = ledPower

                self.trialSet.append(t)

        print str(len(self.trialSet)) + " different trial conditions."

        self.sequencer = Sequencer(self.trialSet, self.sequenceType)
        if self.sequenceType == Sequences.INTERVAL or \
                self.sequenceType == Sequences.INTERVAL_RETRY:
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

        now = time.time()

        if self.state == States.INIT:
            # Wait for the shrew to stop licking, unless its initiation type is
            # LICK
            if self.initiation != Initiation.LICK:
                if self.isLicking or self.lastLickAt > self.stateStartTime:
                    self.stateStartTime = now

            # recompute state end time based on the above
            self.stateEndTime = self.stateStartTime + self.stateDuration

            # -- progression condition -- #
            doneWaiting = False
            if (self.initiation == Initiation.LICK and
                    self.lastLickAt > self.stateStartTime and not
                    self.isLicking):
                # Shrew is supposed to lick, and it has, but it's not licking
                # right now.
                if (now - self.lastLickAt) > 0.5:
                    # In fact, it licked at least half a second ago,
                    # so it should REALLY not be licking now. Let's proceed
                    # with the trial.
                    doneWaiting = True

            elif ((self.initiation == Initiation.TAP or
                   self.initiation == Initiation.TAP_ONSET) and
                  (self.lastTapAt > self.stateStartTime or self.isTapping)):
                doneWaiting = True

            elif self.initiation == Initiation.IR and now > self.stateEndTime:
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

        if self.state == States.SMINUS:
            # -- fail conditions -- #
            # no licking allowed during stimulus
            self.check_fail()

            # -- progression condition -- #
            if now > self.stateEndTime:
                if self.airPuffMode == AirPuffMode.SMINUS_OFFSET:
                    self.training.airPuff.puff()
                    self.training.daq.send_stimcode(STIMCODE_FAIL_PUFF)
                    self.training.log_plot_and_analyze("Puff", time.time())

                self.stateDuration = self.grayDuration
                self.change_state(States.GRAY)

        if self.state == States.GRAY:
            # -- fail conditions -- #
            self.check_fail()

            # -- opto condition -- #
            # This bit of the code catches us as we come out of the SMINUS
            # We reset the optoNow flag when the opto stuff was supposed to
            # have finished.
            if (now >= self.stateStartTime + (self.rampDuration / 1000) and
                    self.useOpto and not
                    self.optoStim2 and
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration. The opto stim should have ended on its own
                # by now, so we reset the opto flag
                self.optoNow = False
                if not self.useOptoFSOnly:
                    self.optoStim2 = True

                self.training.optoController.write('reset0')

            # This bit catches us as we move from gray into the SPLUS
            if (now >= self.stateEndTime - (self.rampDuration / 1000) and
                    self.optoStim2 and
                    self.useOpto and not
                    self.useOptoFSOnly and not
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration
                self.optoNow = True
                power = str(self.currentTrial.ledPower)
                opto_cmd = 'cmd pwr' + power
                self.training.optoController.write(opto_cmd + '\n')
                self.training.log_plot_and_analyze(opto_cmd, time.time())

            # -- progression condition -- #
            if now > self.stateEndTime:
                if self.guaranteedSPlus or self.sMinusDisplaysLeft > 0:
                    # still more gratings to do, continue on
                    self.prepare_grating_state()
                elif self.currentTrial.numSMinus < max(self.sMinusPresentations):
                    # OK, this happens when we have one SMINUS followed by an
                    # SPLUS, e.g. in Chico's task.
                    self.prepare_grating_state()
                else:
                    # There's no SPLUS in this trial,
                    # and we did all the SMINUS displays. All done!
                    self.trialResult = Results.CORRECT_REJECT
                    self.stateDuration = self.timeoutCorrectReject
                    self.change_state(States.TIMEOUT)

        if self.state == States.SPLUS:
            # -- fail conditions -- #
            # no licking allowed
            self.check_fail()

            # -- progression condition -- #
            if now > self.stateEndTime:
                # Possibly dispense a small reward as a hint.
                if self.doHint:
                    self.training.dispense_hint(self.hintBolus / 1000)
                # go to reward state
                self.stateDuration = self.rewardPeriod
                self.change_state(States.REWARD)

        if self.state == States.REWARD:
            # -- opto condition -- #
            # This bit of the code catches us as we come out of the SPLUS
            if (now >= self.stateStartTime + (self.rampDuration / 1000) and
                    self.useOpto and
                    self.optoNow):
                # Changing the flag guarantees us that we won't repeat this for
                # every iteration. The opto stim should have ended on its own
                # by now, so we reset the opto flag
                self.optoNow = False
                self.training.optoController.write('reset0')

            # -- success condition -- #
            if self.lastLickAt >= self.stateStartTime:
                if self.isHighRewardTrial:
                    self.training.dispense_reward(self.rewardBolusHardTrial / 1000)
                else:
                    self.training.dispense_reward(self.rewardBolus / 1000)

                self.stateDuration = self.timeoutSuccess
                self.trialResult = Results.HIT
                self.change_state(States.TIMEOUT)

            # -- progression condition -- #
            if now > self.stateEndTime:
                self.stateDuration = self.timeoutNoResponse
                self.trialResult = Results.NO_RESPONSE
                self.change_state(States.TIMEOUT)

        if self.state == States.TIMEOUT:
            # kill the optogenetics stim, if necessary
            if self.useOpto:
                self.optoNow = False
                self.training.optoController.write('reset0')
                if not self.useOptoFSOnly:
                    self.optoStim2 = False

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

        self.training.log_plot_and_analyze("State" + str(self.state),
                                           time.time())

        # if changed to timeout, reset trial params for the new trial
        if (newState == States.TIMEOUT):
            # tell UI about the trial that just finished
            print Results.whatis(self.trialResult) + "\n"
            self.shrewDriver.sigTrialEnd.emit()

            # prepare next trial
            self.currentTrial = self.sequencer.getNextTrial(self.trialResult)
            self.prepare_trial()
            self.trialNum += 1

        # update screen
        if self.stateDuration > 0:

            if newState == States.SPLUS or newState == States.SMINUS:
                # it's a grating, so call the base grating command
                # and add the orientation and phase

                if self.useMovie:
                    # Here we're co-opting the grating commands to show a movie
                    # instead
                    if newState == States.SPLUS:
                        mov = str(self.currentTrial.sPlusOrientation)
                        mov_path = "movSP" + mov

                    elif newState == States.SMINUS:
                        mov = str(self.currentTrial.sMinusOrientation)
                        mov_path = "movSM" + mov

                    self.training.stimDevice.write(str(self.state) + " " +
                                                   mov_path + "\n")
                    self.training.log_plot_and_analyze(mov_path, time.time())

                else:
                    ori = ""
                    if self.replaceOrientation != "":
                        # If commanded by the UI to swap in a different ori, do so.
                        ori = self.replaceOrientation
                        self.replaceOrientation = ""
                    elif newState == States.SPLUS:
                        ori = str(self.currentTrial.sPlusOrientation)
                    elif newState == States.SMINUS:
                        ori = str(self.currentTrial.sMinusOrientation)

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
        msg = 'state changed to ' + str(States.whatis(newState)) + ' duration ' \
              + str(self.stateDuration)
        if str(States.whatis(newState)) == 'SPLUS':
            msg += ' orientation ' + str(self.currentTrial.sPlusOrientation)
        if str(States.whatis(newState)) == 'SMINUS':
            msg += ' orientation ' + str(self.currentTrial.sMinusOrientation)
            # print msg

    def check_fail(self):
        """Checks to see if the animal failed the trial at any port."""

        # Checks if shrew licks when it shouldn't.
        # Used to check for aborts as well, but IR is no longer used, so that's out.
        # May be used in future with tap sensor.
        if self.isLicking or self.lastLickAt > self.stateStartTime:
            # any other time, licks are bad m'kay
            self.fail()

    def fail(self):
        """Changes state to TASK_FAIL and delivers punishment if necessary.
        This also kills the optogenetics stim if needed."""

        self.stateDuration = self.timeoutFail

        if self.state != States.GRAY:
            self.trialResult = Results.TASK_FAIL

            if (self.airPuffMode == AirPuffMode.TASK_FAIL_LICK or
                    self.airPuffMode == AirPuffMode.BAD_LICK):
                self.training.airPuff.puff()
                self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
                self.training.log_plot_and_analyze("Puff", time.time())
        else:
            self.trialResult = Results.FALSE_ALARM

            if (self.airPuffMode == AirPuffMode.FALSE_ALARM_LICK or
                    self.airPuffMode == AirPuffMode.BAD_LICK):
                self.training.airPuff.puff()
                self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
                self.training.log_plot_and_analyze("Puff", time.time())

        # kill the optogenetics stim, if necessary
        if self.useOpto:
            self.training.optoController.write('reset0')

        self.change_state(States.TIMEOUT)

    def abort(self):
        """Aborts trial based on user fail."""
        self.stateDuration = self.timeoutAbort
        self.trialResult = Results.ABORT
        self.change_state(States.TIMEOUT)

    def prepare_grating_state(self):
        """Prepares the next grating based on the number of remaining S- or
        S- stims."""

        # goes to either SMINUS or SPLUS.
        # this has its own function because it's called from both DELAY and GRAY.
        if self.sMinusDisplaysLeft > 0:
            self.stateDuration = self.gratingDuration
            self.change_state(States.SMINUS)
            self.sMinusDisplaysLeft -= 1
        else:
            # finished all SMINUS displays
            if (self.guaranteedSPlus or
                    self.currentTrial.numSMinus < max(self.sMinusPresentations) or
                    max(self.sMinusPresentations) == 0):
                # continue to SPLUS
                self.stateDuration = self.gratingDuration
                self.change_state(States.SPLUS)
            else:
                self.trialResult = Results.CORRECT_REJECT
                self.stateDuration = self.timeoutCorrectReject
                self.change_state(States.TIMEOUT)

    # --- Interactive UI commands --- #
    def ui_start_trial(self):
        """Start a trial when user presses the button on the UI."""

        if self.state == States.TIMEOUT or self.state == States.INIT:
            self.training.log_plot_and_analyze("User started trial",
                                               time.time())
            print "User started trial"
            self.stateDuration = random.uniform(self.variableDelayMin,
                                                self.variableDelayMax)
            self.training.daq.send_stimcode(STIMCODE_USER_TRIAL)
            # Wait one millisecond before changing anything
            time.sleep(0.001)
            self.change_state(States.DELAY)

    def ui_fail_task(self):
        """Fail a trial when user presses the button on the UI."""

        self.training.log_plot_and_analyze("Trial failed at user's request",
                                           time.time())
        print "Trial failed at user's request"
        self.training.daq.send_stimcode(STIMCODE_AIR_PUFF)
        self.fail()

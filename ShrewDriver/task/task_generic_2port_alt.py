# TaskGeneric_2port_alt: task_generic_2port_alt.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 13 March 2018

from __future__ import division
import fileinput
import re
import math
import random
import time
import sys
from task_mixin_2AFC import *
from trial import Trial

sys.path.append("..")
from sequencer.sequencer_base import Sequencer


class TaskGeneric_2port_alt(TaskMixin_2AFC):
    """
    A stimless task used for acclimation on all animals with no animal-specific
    parameters. TaskHeadfix_GNG is a one-syringe lick to get reward task, with
    imposed post-lick cool down. TaskHeadfix_2AFC is a two-syringe lick to get
    reward task, with imposed post-lick cool down. TaskHeadfix_2AFC1 is like
    TaskHeadfix_2AFC, except that switching between left and right syringe
    ports are imposed. the variable alternate_n defines how many repeats are
    necessary before alternating. Currently, the counter isn't reset if the
    shrew switches to the other side incorrectly.
    """

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

        self.make_stuff()

    def start(self):
        """Set initial state to INIT and initialize side counts"""

        # have both spouts open to start
        self.change_state(States.INIT)
        # self.change_state(States.REWARD)
        self.side_count_left = 0
        self.side_count_right = 0

    def check_state_progression(self):
        """Checks the current state and determines what do do next"""

        now = time.time()
        # print self.shrewDriver.alternate_n

        # If you just got a left reward, and you've gotten n left rewards
        if (self.state == States.TIMEOUT_LEFT and
                self.side_count_left >= self.shrewDriver.alternate_n):
            # Wait for shrew to lick on the right
            if self.isRightLicking:
                self.side_count_left = 0
                self.side_count_right = self.side_count_right + 1
                self.training.dispense_reward_right(self.rewardBolus / 1000)
                self.change_state(States.TIMEOUT_RIGHT)

        # if we're still below required number of licks before we alternate to
        # other side
        elif (self.state == States.TIMEOUT_LEFT and
                self.side_count_left < self.shrewDriver.alternate_n):
            timeSinceLeftLick = now - self.lastLeftLickAt
            timeSinceStateStart = now - self.stateStartTime

            if (timeSinceStateStart > self.rewardCooldown and not
                    self.isLeftLicking and
                    timeSinceLeftLick > self.rewardCooldown):
                # Shrew hasn't licked for a while, so make reward available
                self.change_state(States.REWARD_LEFT)

        # If you were just given a left reward, wait for shrew to stop licking
        # and go into left timeout until there's a lick on the right
        if self.state == States.REWARD_LEFT or self.state == States.INIT:

            # Wait for the shrew to stop licking
            if self.lastLeftLickAt > self.stateStartTime and self.lastLeftLickAt != 0:
                self.side_count_left = self.side_count_left + 1
                self.training.dispense_reward_left(self.rewardBolus / 1000)
                self.change_state(States.TIMEOUT_LEFT)

        # -- now for the other port -- #

        if (self.state == States.TIMEOUT_RIGHT and
                self.side_count_right >= self.shrewDriver.alternate_n):

            # Wait for shrew to lick on the right
            if self.isLeftLicking:
                self.side_count_right = 0
                self.side_count_left = self.side_count_left + 1
                self.training.dispense_reward_left(self.rewardBolus / 1000)
                self.change_state(States.TIMEOUT_LEFT)

        # if we're still below required number of licks before we alternate to
        # other side
        elif (self.state == States.TIMEOUT_RIGHT and
                self.side_count_right < self.shrewDriver.alternate_n):
            timeSinceRightLick = now - self.lastRightLickAt
            timeSinceStateStart = now - self.stateStartTime

            if (timeSinceStateStart > self.rewardCooldown and not
                    self.isRightLicking and
                    timeSinceRightLick > self.rewardCooldown):
                # Shrew hasn't licked for a while, so make reward available
                self.change_state(States.REWARD_RIGHT)

        if self.state == States.REWARD_RIGHT or self.state == States.INIT:
            # Wait for the shrew to stop licking
            if self.lastRightLickAt > self.stateStartTime and self.lastRightLickAt != 0:
                self.side_count_right = self.side_count_right + 1
                self.training.dispense_reward_right(self.rewardBolus / 1000)
                self.change_state(States.TIMEOUT_RIGHT)

    def change_state(self, newState):
        """
        Changes the state progression to the new state and logs the change. If
        the new state is any kind of timeout, it resets trial parameters for a
        new trial.

        Args:
            newState: [int] the new state to be presented
        """

        # runs every time a state changes
        # self.training.log_plot_and_analyze("State" + str(self.state), time.time())
        self.stateStartTime = time.time()
        self.state = newState

        # if changed to timeout, reset trial params for the new trial
        if newState == States.TIMEOUT_LEFT or newState == States.TIMEOUT_RIGHT:
            # tell UI about the trial that just finished
            self.shrewDriver.sigTrialEnd.emit()

        # print 'state changed to ' + str(States.whatis(newState))
        # print  'last right lick at ' + str(self.lastRightLickAt)
        # print  'last leftlick at ' + str(self.lastLeftLickAt)

    def make_trial_set(self):
        pass

    def prepare_trial(self):
        pass

    # --- Interactive UI commands ---#
    def ui_start_trial(self):
        """Start a trial when user presses the button on the UI."""

        if (self.state == States.TIMEOUT_LEFT or
                self.state == States.TIMEOUT_RIGHT or
                self.state == States.INIT):
            self.training.log_plot_and_analyze("User started trial")
            print "User started trial"
            self.change_state(States.REWARD_LEFT)
            self.change_state(States.REWARD_RIGHT)

    def ui_fail_task(self):
        """Fail a trial when user presses the button on the UI."""

        self.training.log_plot_and_analyze("Trial failed at user's request",
                                           time.time())
        print "Trial failed at user's request"
        self.fail()

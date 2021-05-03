from __future__ import division
import sys
sys.path.append("..")


import fileinput
import re
import math
import random
import time

from task_mixin import *

from sequencer.sequencer_base import Sequencer
from trial import Trial

class TaskGeneric_1port(TaskMixin):
    """A stimless task used for acclimation on all animals with no
    animal-specific parameters"""

    def __init__(self, training, shrewDriver):
        self.training = training
        self.shrewDriver = shrewDriver
        self.animalName = self.shrewDriver.animalName

        # flag for potential optogenetics stuff
        self.useOpto = self.shrewDriver.useOpto
        self.useOptoFSOnly = self.shrewDriver.useOptoFSOnly
        self.optoNow = False

        self.make_stuff()

    def start(self):
        self.change_state(States.REWARD)
    
    def check_state_progression(self):
        now = time.time()
        
        if self.state == States.TIMEOUT:
            timeSinceLick = now - self.lastLickAt
            timeSinceStateStart = now - self.stateStartTime
            if timeSinceStateStart > self.rewardCooldown and not self.isLicking and timeSinceLick > self.rewardCooldown:
                #Shrew hasn't licked for a while, so make reward available
                self.change_state(States.REWARD)
               
        if self.state == States.REWARD:
            #Wait for the shrew to stop licking
            if self.lastLickAt > self.stateStartTime and self.lastLickAt != 0:
                self.training.dispense_reward(random.choice(self.rewardBolus) / 1000)
                self.change_state(States.TIMEOUT)
                
    def change_state(self, newState):
        #runs every time a state changes
        #self.training.log_plot_and_analyze("State" + str(self.state), time.time())
        self.stateStartTime = time.time()
        self.state = newState
        
        #if changed to timeout, reset trial params for the new trial
        if (newState == States.TIMEOUT):
            #tell UI about the trial that just finished
            self.shrewDriver.sigTrialEnd.emit()
        
        #print 'state changed to ' + str(States.whatis(newState))

    def make_trial_set(self):
        pass

    def prepare_trial(self):
        pass

    #--- Interactive UI commands ---#
    def ui_start_trial(self):
        if self.state == States.TIMEOUT or self.state == States.INIT:
            self.training.log_plot_and_analyze("User started trial")
            print "User started trial"
            self.change_state(States.REWARD)

    def ui_fail_task(self):
        self.training.log_plot_and_analyze("Trial failed at user's request", time.time())
        print "Trial failed at user's request"
        self.fail()


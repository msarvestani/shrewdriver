# TaskMixin_2AFC: task_mixin_2AFC.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 14 March 2018

from __future__ import division
import time
import traceback
import sys
sys.path.append("..")
from constants.task_constants_2AFC import *
from util.enumeration import *
from util.serialize import objectToString
from sequencer.sequencer_base import Sequencer


class TaskMixin_2AFC(object):
    """Defines a set of functions used across all classes"""

    def make_stuff(self):
        """Initializes variables, etc. Called from task class inits. Prepares
        the stimulus device, loads animal settings, writes settings files, and
        creates the trial set."""

        # behavior inits
        self.state = States.TIMEOUT
        self.stateDuration = 1
        self.shrewPresent = False
        self.shrewEnteredAt = 0
        self.isLeftLicking = False
        self.isRightLicking = False
        self.isCenterLicking = False
        self.lastLeftLickAt = 0
        self.lastRightLickAt = 0
        self.lastCenterLickAt = 0
        self.isLicking = False
        self.lastLickAt = 0
        self.stateStartTime = 0
        self.stateEndTime = 0
        self.showInteractUI = False
        self.commandStrings = [''] * len(stateSet)
        
        # load and record this session's settings
        self.load_animal_settings()
        self.write_settings_file()

        # send commands to prepare stimbot
        self.set_up_commands()

        # make a set of trial objects and a sequencer
        self.make_trial_set()

        # set up the first trial
        if hasattr(self, 'sequencer'):
            self.currentTrial = self.sequencer.getNextTrial(None)

        self.prepare_trial()
        self.trialNum = 1

    def set_up_commands(self):
        """set up stimbot commands for later use"""

        # send animal-specific movie directory to stimDevice (Doris Tsao collab)
        self.training.stimDevice.write('screendist' +
                                       str(self.screenDistanceMillis) +
                                       ' setSPD&' + self.sPlusDir + '\n')

        # We send this one separately since it will be read later
        self.training.stimDevice.write('setSMD&' + self.sMinusDir + '\n')

        for i in xrange(0, len(stateSet)):
            # wait a bit between long commands to make sure
            # serial sends everything
            time.sleep(0.1)
            saveCommand = 'save' + str(i) + ' ' + self.commandStrings[i]
            self.training.stimDevice.write(saveCommand)
    
    def sensor_update(self, evtType, timestamp):
        """
        Updates licking states, last lick/tap/IR beam times.
        Args:
            evtType: [str] the event type as read from the Arduino sensors
            timestamp: [float] current time stamp

        Returns: updated object variables with new time stamps and booleans
        """

        if evtType == 'Ix':
            self.shrewPresent = True
            self.shrewEnteredAt = time.time()

        if evtType == 'Io':
            self.shrewPresent = False

        if evtType.startswith('RIGHTLx'):
            self.isRightLicking = True
            self.lastRightLickAt = time.time()
            self.isLicking = True
            self.lastLickAt = time.time()

        if evtType == 'RIGHTLo':
            self.isRightLicking = False
            self.isLicking = False

        if evtType.startswith('LEFTLx'):
            self.isLeftLicking = True
            self.lastLeftLickAt = time.time()
            self.isLicking = True
            self.lastLickAt = time.time()

        if evtType == 'LEFTLo':
            self.isLeftLicking = False
            self.isLicking = False

        if evtType.startswith('CENTERLx'):
            self.isCenterLicking = True
            self.lastCenterLickAt = time.time()
            self.isLicking = True
            self.lastLickAt = time.time()

        if evtType == 'CENTERLo':
            self.isCenterLicking = False
            self.isLicking = False

            # self.lastLickAt = time.time()
    
    def write_settings_file(self):
        """Sets path to settings and summary files, and creates the files."""

        self.settingsFilePath = self.shrewDriver.experimentPath \
                                + self.shrewDriver.sessionFileName \
                                + "_settings.txt"
        self.summaryFilePath = self.shrewDriver.experimentPath \
                               + self.shrewDriver.sessionFileName \
                               + "_summary.txt"
        self.settingsFile = open(self.settingsFilePath, 'w')
        self.settingsFile.write("States: " + str(stateSet) + "\n")
        thisAsString = objectToString(self)
        self.settingsFile.write(thisAsString)
        self.settingsFile.close()
    
    def load_animal_settings(self):
        """Loads the shrew/---.py or ---_2AFC.py files for task parameters.
        Uses a (questionable) exec method to import the variables and then
        evaluate the load_parameters() function in the shrew file."""

        try:
            if self.animalName == 'Generic':
                print "Importing settings from shrew/" + self.animalName.lower() + ".py"
                sys.stdout.flush()
                importStatement = "from shrew." + self.animalName.lower() + " import load_parameters"

                exec(importStatement)
                # this is just an eval so the code editor won't complain about
                # missing imports
                eval("load_parameters(self)")

            else:
                print "Importing settings from shrew/" + self.animalName.lower() + "_2AFC.py"
                sys.stdout.flush()
                importStatement = "from shrew." + self.animalName.lower() + "_2AFC" + " import load_parameters"
                exec(importStatement)
                # this is just an eval so the code editor won't complain about
                # missing imports
                eval("load_parameters(self)")

        except():
            print "Error - couldn't load shrew/" + self.animalName.lower() + ".py!"
            print "Check that the file exists and has a load_settings function."
            traceback.print_exc()
            raise()

# Class containing analysis functions for the generic task used at the very
# beginning of training. These classes process events and update the reward
# volume delivered, while providing the strings that get printed on the UI.
# Valid for 1 and 2 port cases.

from __future__ import division
import re
from collections import deque


class GenericAnalysis_2port:

    def __init__(self, logFile=None, settingsFile=None, notesFile=None):

        self.logFile = logFile
        self.settingsFile = settingsFile
        self.notesFile = notesFile

        # Set up a double ended queue (see documentation for performance)
        self.eventsToProcess = deque()

        self.totalmL_left = 0
        self.totalmL_right = 0
        self.p = re.compile('\d+')
        
    def event(self, event):
        """Append events to deque for processing"""
        self.eventsToProcess.append(event)

    def process_events(self):
        """
        Process all the events in the deque. 
        Should be called at the end of each trial.
        Not threadsafe; expecting this to be used in-thread between trials.
        """
        while len(self.eventsToProcess) > 0:
            line = self.eventsToProcess.popleft()
            self.process_line(line)

    def get_results_str(self):
        """Returns string to be printed to text box on UI"""
        return "Total mL : " + str(self.totalmL_left + self.totalmL_right)\
               + "\nLeft: " + str(self.totalmL_left) + "\nRight: " + str(self.totalmL_right)

    def process_line(self, line):
        """Searches even string for user rewards or boluses, and increments total
        volume of reward given."""
        if "left_bolus" in line or "user_reward_left" in line:
            # print line
            m = self.p.findall(line)
            mL = float(m[0] + "." + m[1])
            self.totalmL_left += mL

        if "right_bolus" in line or "user_reward_right" in line:
            # print line
            m = self.p.findall(line)
            mL = float(m[0] + "." + m[1])
            self.totalmL_right += mL

    def get_summary_path(self):
        """Use the settings file path to create the summary file path"""
        return self.settingsFile.replace("settings", "summary")


class GenericAnalysis_1port:
    def __init__(self, logFile=None, settingsFile=None, notesFile=None):
        self.logFile = logFile
        self.settingsFile = settingsFile
        self.notesFile = notesFile

        self.eventsToProcess = deque()

        self.totalmL = 0
        self.p = re.compile('\d+')

    def event(self, event):
        """Append events to deque for processing"""
        self.eventsToProcess.append(event)

    def process_events(self):
        """
        Process all the events in the deque.
        Should be called at the end of each trial.
        Not threadsafe; expecting this to be used in-thread between trials.
        """
        while len(self.eventsToProcess) > 0:
            line = self.eventsToProcess.popleft()
            self.process_line(line)

    def get_results_str(self):
        """Returns string to be printed to text box on UI"""
        return "Total mL: " + str(self.totalmL)

    def process_line(self, line):
        """Searches even string for user rewards or boluses, and increments total
                volume of reward given."""
        if "bolus" in line or "user_reward" in line:
            # print line
            m = self.p.findall(line)
            mL = float(m[0] + "." + m[1])
            self.totalmL += mL

    def get_summary_path(self):
        """Use the settings file path to create the summary file path"""
        return self.settingsFile.replace("settings", "summary")

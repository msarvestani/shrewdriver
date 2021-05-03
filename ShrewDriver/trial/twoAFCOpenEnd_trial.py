# TwoAFCOpenEndTrial: twoAFCOpenEnd_trial.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 01/09/2017

from __future__ import division
import sys
sys.path.append("..")
from analysis.twoafc_openend_analysis import *


class TwoAFCOpenEndTrial:
    """One trial of a discrimination task."""

    def __init__(self, analysis=None):
        """
        Args:
            analysis: [object] analyzer as defined in the analysis directory
        """

        self.analysis = analysis    # TwoAFCOpenEndAnalysis
        self.sLeftPresentations = self.analysis.sLeftPresentations
        self.sLeftOrientations = self.analysis.sLeftOrientations
        self.sRightOrientations = self.analysis.sRightOrientations

        self.sLeftOrientation = -1
        self.sRightOrientation = -1

        self.numSLeft = 0           # number of times SLeft was presented

        self.trialStartTime = 0
        self.hint_left = False      # true if hint_left was dispensed
        self.reward_left = False    # true if reward_left was dispensed
        self.totalmL_left = 0
        self.hint_right = False     # true if hint_right was dispensed
        self.reward_right = False   # true if reward_right was dispensed
        self.totalmL_right = 0
        self.totalmL = 0
        self.hintmL_left = 0
        self.hintmL_right = 0
        self.hintmL = 0
        self.trialNum = 0

        # results
        self.result = None
        self.resultState = None
        self.hint = True

        self.hintTime = None
        self.rewardTime = None

        self.stateHistory = []
        self.stateTimes = []
        self.actionHistory = []
        self.actionTimes = []

        # stores logfile lines until trial is finished and ready to be analyzed
        self.lines = []

    def analyze(self):
        """Scrapes lines from the log file to figure out what happened during
        a trial."""

        p = re.compile('\d+')

        # determine what movies were used in this trial
        for line in self.lines:

            if re.search('movSP', line):
                toks = line.split()
                mov = toks[0][5:]
                self.sLeftOrientation = int(mov)

            if re.search('movSM', line):
                toks = line.split()
                mov = toks[0][5:]
                self.sRightOrientation = int(mov)

        # record events
        for line in self.lines:
            if re.search('LeftRL', line):
                # left hint
                self.hint_left = True
                m = p.findall(line)
                self.hintLeftTime = float(m[0] + '.' + m[1])
            elif re.search('RightRL', line):
                # right hint
                self.hint_right = True
                m = p.findall(line)
                self.hintRightTime = float(m[0] + '.' + m[1])
            elif re.search('LeftRH', line):
                # left reward
                self.reward_left = True
                m = p.findall(line)
                self.rewardTime_left = float(m[0] + '.' + m[1])
            elif re.search('RightRH', line):
                # right reward
                self.reward_right = True
                m = p.findall(line)
                self.rewardTime_right = float(m[0] + '.' + m[1])
            elif re.search('bolus', line):
                # bolus volume
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL += bolusSize
            elif re.search('user_reward_left', line):
                # bolus volume of user hint left
                linesub = line[line.find('user_reward_left'):]
                m = p.findall(linesub)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_left += bolusSize
                self.hintmL_left += bolusSize
            elif re.search('user_reward_right', line):
                # bolus volume of user hint right
                linesub = line[line.find('user_reward_right'):]
                m = p.findall(linesub)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_right += bolusSize
                self.hintmL_right += bolusSize
            elif re.search('hint_left', line):
                # bolus volume of left hint
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_left += bolusSize
                self.hintmL_left += bolusSize
            elif re.search('hint_right', line):
                # bolus volume of right hint
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_right += bolusSize
                self.hintmL_right += bolusSize

            elif re.search('LEFTLx', line):
                # left lick
                self.isLeftLicking = True
                self.actionHistory.append(Actions.LEFT_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('LEFTLo', line):
                # end left lick
                self.isLicking = False
                self.actionHistory.append(Actions.LEFT_LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('RIGHTLx', line):
                # right lick
                self.actionHistory.append(Actions.RIGHT_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('RIGHTLo', line):
                # end right lick
                self.actionHistory.append(Actions.RIGHT_LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('CENTERLx', line):
                # center lick
                self.actionHistory.append(Actions.CENTER_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('CENTERLo', line):
                # end center lick
                self.actionHistory.append(Actions.CENTER_LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))

        # examine what states occurred
        for line in self.lines:
            if re.search('State', line):
                m = p.findall(line)
                self.stateHistory.append(int(m[0]))
                self.stateTimes.append(float(m[1] + "." + m[2]))

                if self.stateHistory[-1] == States.INIT:
                    self.trialStartTime = float(m[1] + "." + m[2])

                if self.stateHistory[-1] == States.SLEFT:
                    self.numSLeft += 1

                if len(self.stateHistory) < 3:
                    # Usually means task was assigned a fail state by user
                    # input
                    self.result = Results.TASK_FAIL

                elif self.stateHistory[-1] == States.TIMEOUT:
                    self.result = Results.TASK_FAIL

                elif self.stateHistory[-1] == States.TIMEOUT_LEFT:
                    # end of trial
                    # Figure out what the trial result was based on actions
                    # and states
                    prevState = self.stateHistory[-2]
                    prevStateStart = self.stateTimes[-2]
                    self.resultState = prevState

                    if self.reward_left:
                        # it's a HIT_LEFT.
                        self.result = Results.HIT_LEFT

                    else:
                        # No reward earned; it's a MISS since we cannot have
                        # a NO_RESPONSE flag or a TASK_FAIL_LEFT flag.
                        self.result = Results.MISS_LEFT

                elif self.stateHistory[-1] == States.TIMEOUT_RIGHT:

                    # end of trial
                    # Figure out what the trial result was based on actions
                    # and states
                    prevState = self.stateHistory[-2]
                    prevStateStart = self.stateTimes[-2]
                    self.resultState = prevState

                    if self.reward_right:
                        # it's a HIT_RIGHT.
                        self.result = Results.HIT_RIGHT

                    else:
                        # No reward earned; it's a MISS since we cannot have
                        # a NO_RESPONSE flag or a TASK_FAIL_RIGHT flag.
                        self.result = Results.MISS_RIGHT

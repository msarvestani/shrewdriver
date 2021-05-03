# GNGTrial: gonogo_trial.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 15 March 2018

from __future__ import division
import sys
sys.path.append("..")
from analysis.gonogo_analysis import *


class GNGTrial:
    """One trial of a discrimination task."""

    def __init__(self, analysis=None):
        """
        Args:
            analysis: [object] analyzer as defined in the analysis directory
        """

        self.analysis = analysis  # type GonogoAnalysis
        self.guaranteedSPlus = self.analysis.guaranteedSPlus
        self.sMinusPresentations = self.analysis.sMinusPresentations
        self.sMinusOrientations = self.analysis.sMinusOrientations
        self.sPlusOrientations = self.analysis.sPlusOrientations

        self.sMinusOrientation = -1
        self.sPlusOrientation = -1
        self.ledPower = -1

        # number of times SMINUS was presented
        self.numSMinus = 0

        self.trialStartTime = 0
        self.hint = False    # [bool] true if hint was dispensed
        self.reward = False  # [bool] true if reward was dispensed
        self.totalmL = 0
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

        # determine what orientations were used in this trial
        for line in self.lines:
            if re.search('ori', line) or re.search('sqr', line):
                toks = line.split()
                ori = toks[0][3:]

                if float(ori) in self.sMinusOrientations:
                    self.sMinusOrientation = float(ori)
                else:
                    self.sPlusOrientation = float(ori)

        # record events
        for line in self.lines:
            if re.search('RL', line):
                # Right hint
                self.hint = True
                m = p.findall(line)
                self.hintTime = float(m[0] + '.' + m[1])
            elif re.search('RH', line):
                # Right reward
                self.reward = True
                m = p.findall(line)
                self.rewardTime = float(m[0] + '.' + m[1])
            elif re.search('bolus', line):
                # Bolus volume
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL += bolusSize
            elif re.search('user_reward', line):
                # user-delivered reward volume
                linesub = line[line.find('user_reward'):]
                m = p.findall(linesub)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL += bolusSize
                self.hintmL += bolusSize
            elif re.search('hint', line):
                # hint bolus volume
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL += bolusSize
                self.hintmL += bolusSize

            elif re.search('LEFTLx', line):
                # Left lick
                self.isLicking = True
                self.actionHistory.append(Actions.LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('LEFTLo', line):
                # End left lick
                self.isLicking = False
                self.actionHistory.append(Actions.LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            # Override the tap sensor for right lick on 2AFC task
            elif re.search('RIGHTLx', line):
                # Right lick
                self.actionHistory.append(Actions.TAP)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('RIGHTLo', line):
                # End right lick
                self.actionHistory.append(Actions.TAP_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            elif re.search('Io', line):
                # Exit IR beam path (no longer used)
                self.actionHistory.append(Actions.LEAVE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))

        # examine what states occurred
        for line in self.lines:
            if re.search('State', line):
                m = p.findall(line)
                self.stateHistory.append(int(m[0]))
                self.stateTimes.append(float(m[1] + "." + m[2]))

                if self.stateHistory[-1] == States.DELAY:
                    self.trialStartTime = float(m[1] + "." + m[2])

                if self.stateHistory[-1] == States.SMINUS:
                    self.numSMinus += 1

                if len(self.stateHistory) < 3:
                    # Usually means task was assigned a fail state by user input
                    self.result = Results.TASK_FAIL

                elif self.stateHistory[-1] == States.TIMEOUT:
                    # End of trial. Figure out what the trial result was based
                    # on actions and states
                    prevState = self.stateHistory[-2]
                    prevStateStart = self.stateTimes[-2]
                    self.resultState = prevState

                    if self.reward:
                        # could be a HIT or CORRECT_REJECT.
                        if self.guaranteedSPlus == False:
                            # the only lick result with a reward is HIT
                            self.result = Results.HIT
                        elif self.guaranteedSPlus == True:
                            # could be an sMinus or sPlus trial, let's find out
                            if self.numSMinus == max(self.sMinusPresentations):
                                # S- trial, so CR
                                self.result = Results.CORRECT_REJECT
                            else:
                                # S+ trial, so hit
                                self.result = Results.HIT

                    else:
                        # no reward earned; could be an ABORT, FALSE_ALARM,
                        # TASK_FAIL, MISS, NO_RESPONSE,or CORRECT_REJECT.
                        if prevState == States.DELAY:
                            # shrew was already licking when delay state began,
                            # causing an instant fail
                            self.result = Results.TASK_FAIL

                        elif (len(self.actionHistory) > 0 and
                              self.actionHistory[-1] == Actions.LEAVE and
                              self.actionTimes[-1] >= prevStateStart):
                            # final action was leaving, and it led to the
                            # timeout. Was an aborted trial.
                            self.result = Results.ABORT

                        elif (len(self.actionHistory) > 0 and
                              self.actionHistory[-1] == Actions.LICK and
                              self.actionTimes[-1] >= prevStateStart):
                            # lick caused trial to end; could be FALSE_ALARM or
                            # TASK_FAIL.
                            if prevState == States.GRAY:
                                if (self.numSMinus == 1 and
                                        min(self.sMinusPresentations) == 1):
                                    # it was during the memory delay on a
                                    #  template task. It's a task error.
                                    self.result = Results.TASK_FAIL
                                else:
                                    # Test grating was just presented; this is
                                    # a false alarm.
                                    self.result = Results.FALSE_ALARM
                            else:
                                # licks in any other states are screwups
                                self.result = Results.TASK_FAIL
                        else:
                            # trial ended on its own, so it's a MISS, NO_RESPONSE,
                            # or CORRECT_REJECT.
                            if (self.guaranteedSPlus and
                                    self.numSMinus == max(self.sMinusPresentations)):
                                self.result = Results.NO_RESPONSE
                            elif (not self.guaranteedSPlus and
                                  prevState == States.GRAY):
                                self.result = Results.CORRECT_REJECT
                            else:
                                self.result = Results.MISS

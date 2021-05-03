# TwpAFCTrial: Twoafc_trial.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 15 March 2018

from __future__ import division
import sys
sys.path.append("..")
from analysis.twoafc_analysis import *


class TwoAFCTrial:
    """One trial of a discrimination task."""

    def __init__(self, analysis=None):
        """
        Args:
            analysis: [object] analyzer as defined in the analysis directory
        """

        self.analysis = analysis  # type: TwoAFCAnalysis
        self.sLeftPresentations = self.analysis.sLeftPresentations
        self.sLeftOrientations = self.analysis.sLeftOrientations
        self.sRightOrientations = self.analysis.sRightOrientations

        self.sLeftOrientation = -1
        self.sRightOrientation = -1

        # number of times SLeft was presented
        self.numSLeft = 0

        self.trialStartTime = 0
        self.hint_left = False     # bool, true if hint_left was dispensed
        self.reward_left = False   # bool, true if reward_left was dispensed
        self.totalmL_left = 0
        self.hint_right = False    # bool, true if hint_right was dispensed
        self.reward_right = False  # bool, true if reward_right was dispensed
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

        # determine what orientations were used in this trial
        for line in self.lines:

            if re.search('ori', line) or re.search('sqr', line):
                toks = line.split()
                ori = toks[0][3:]

                if float(ori) in self.sLeftOrientations:
                    self.sLeftOrientation = float(ori)
                else:
                    self.sRightOrientation = float(ori)

            # we also might be using movies instead of orientations,
            # so be ready for that
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

            # -- rewards and such -- #
            if re.search('LeftRL', line):
                # hint left
                self.hint_left = True
                m = p.findall(line)
                self.hintLeftTime = float(m[0] + '.' + m[1])

            elif re.search('RightRL', line):
                # hint right
                self.hint_right = True
                m = p.findall(line)
                self.hintRightTime = float(m[0] + '.' + m[1])

            elif re.search('LeftRH', line):
                # reward left
                self.reward_left = True
                m = p.findall(line)
                self.rewardTime_left = float(m[0] + '.' + m[1])

            elif re.search('RightRH', line):
                # reward right
                self.reward_right = True
                m = p.findall(line)
                self.rewardTime_right = float(m[0] + '.' + m[1])

            elif re.search('bolus', line):
                # bolus volume
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL += bolusSize

            elif re.search('user_reward_left', line):
                # user reward bolus volume to left
                linesub = line[line.find('user_reward_left'):]
                m = p.findall(linesub)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_left += bolusSize
                self.hintmL_left += bolusSize

            elif re.search('user_reward_right', line):
                # user reward bolus volume to right
                linesub = line[line.find('user_reward_right'):]
                m = p.findall(linesub)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_right += bolusSize
                self.hintmL_right += bolusSize

            elif re.search('hint_left', line):
                # bolus volume for hint to left
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_left += bolusSize
                self.hintmL_left += bolusSize

            elif re.search('hint_right', line):
                # bolus volume for hint to right
                m = p.findall(line)
                bolusSize = float(m[0] + "." + m[1])
                self.totalmL_right += bolusSize
                self.hintmL_right += bolusSize

            # -- licks and such -- #
            elif re.search('LEFTLx', line):
                # lick left
                self.isLeftLicking = True
                self.actionHistory.append(Actions.LEFT_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            elif re.search('LEFTLo', line):
                # end lick left
                self.isLicking = False
                self.actionHistory.append(Actions.LEFT_LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            elif re.search('RIGHTLx', line):
                # lick right
                self.actionHistory.append(Actions.RIGHT_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            elif re.search('RIGHTLo', line):
                # end lick right
                self.actionHistory.append(Actions.RIGHT_LICK_DONE)
                m = p.findall(line)
                self.actionTimes.append(float(m[0] + '.' + m[1]))
            elif re.search('CENTERLx', line):
                # lick center
                self.actionHistory.append(Actions.CENTER_LICK)
                m = p.findall(line.split()[1])
                self.actionTimes.append(float(m[0] + '.' + m[1]))

            elif re.search('CENTERLo', line):
                # end lick center
                self.actionHistory.append(Actions.CENTER_LICK_DONE)
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

                if self.stateHistory[-1] == States.SLEFT:
                    self.numSLeft += 1

                if len(self.stateHistory) < 3:
                    # Usually means task was assigned a fail state by user input
                    self.result = Results.TASK_FAIL

                elif self.stateHistory[-1] == States.TIMEOUT:
                    self.result = Results.TASK_FAIL

                elif self.stateHistory[-1] == States.TIMEOUT_LEFT:
                    # End of trial. Figure out what the trial result was based
                    # on actions and states
                    prevState = self.stateHistory[-2]
                    prevStateStart = self.stateTimes[-2]
                    self.resultState = prevState

                    if self.reward_left:
                        # it's a HIT_LEFT.
                        self.result = Results.HIT_LEFT

                    else:
                        # no reward earned; could be an TASK_FAIL, MISS or
                        # NO_RESPONSE_LEFT
                        if prevState == States.DELAY:
                            # shrew was already licking when delay state
                            # began, causing an instant fail
                            self.result = Results.TASK_FAIL_LEFT

                        elif (len(self.actionHistory) > 0 and
                              self.actionHistory[-1] == Actions.LEFT_LICK and
                              self.actionTimes[-1] >= prevStateStart):
                            # leftlick caused (nonrewarded) trial to end;
                            # could be TASK_FAIL.
                            self.result = Results.TASK_FAIL_LEFT

                        elif (prevState == States.SLEFT and len(self.actionHistory) > 0 and
                                        self.actionHistory[-1] == Actions.RIGHT_LICK and
                                        self.actionTimes[-1] >= prevStateStart):
                            # right lick caused  (nonrewarded) trial to end;
                            # could be a MISS or a TASK_FAIL
                            self.result = Results.TASK_FAIL_LEFT

                        elif (prevState == States.REWARD_LEFT and len(self.actionHistory) > 0 and
                                        self.actionHistory[-1] == Actions.RIGHT_LICK and
                                        self.actionTimes[-1] >= prevStateStart):
                            # right lick caused  (nonrewarded) trial to end
                            # could be a MISS or a TASK_FAIL
                            self.result = Results.MISS_LEFT

                        else:
                            # trial ended on its own, so it's NO_RESPONSE
                            self.result = Results.NO_RESPONSE_LEFT

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
                        # no reward earned; could be an TASK_FAIL, MISS or
                        # NO_RESPONSE_RIGHT
                        if prevState == States.DELAY:
                            # shrew was already licking when delay state began,
                            # causing an instant fail
                            self.result = Results.TASK_FAIL_RIGHT

                        elif (len(self.actionHistory) > 0 and
                              self.actionHistory[-1] == Actions.RIGHT_LICK and
                              self.actionTimes[-1] >= prevStateStart):
                            self.result = Results.TASK_FAIL_RIGHT

                        elif (prevState == States.SRIGHT and
                              len(self.actionHistory) > 0 and
                              self.actionHistory[-1]  == Actions.LEFT_LICK and
                              self.actionTimes[-1] >= prevStateStart):
                            # right lick caused trial to end; could be a MISS
                            self.result = Results.TASK_FAIL_RIGHT

                        elif (prevState == States.REWARD_RIGHT and
                              len(self.actionHistory) > 0 and
                              self.actionHistory[-1] == Actions.LEFT_LICK and
                              self.actionTimes[-1] >= prevStateStart):
                            # right lick caused trial to end; could be a MISS
                            self.result = Results.MISS_RIGHT

                        else:
                            # trial ended on its own, so it's NO_RESPONSE
                            self.result = Results.NO_RESPONSE_RIGHT

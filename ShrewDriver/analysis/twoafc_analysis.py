# Class containing analysis functions for the 2AFC task. Reads in the log and
# settings files, and parses the log file to reconstruct the experiment and
# display the statistics on the UI

from __future__ import division
import sys
import re
import fileinput
import glob
import os
import datetime
sys.path.append("..")

from util.enumeration import Enumeration
from util.cache_decorators import *
from constants.task_constants_2AFC import *
from trial.Twoafc_trial import *
from util.human import seconds_to_human

"""
Analyzes data.
Reads in the log and settings files.
Produces a set of trials.
"""


class OrientationPerformance:
    def __init__(self):
        """Used in tabulating performance for display"""
        self.numTrials = 0
        self.numCorrect = 0
        self.percentCorrect = 0


# This is for analyzing data, based on the raw log file and settings file.
class TwoAFCAnalysis:
    """
    Analyzes a single log file.
    Requires the corresponding settings file.
    Init will read in files, then you can use the get_performance functions to
    summarize results.
    """

    def __init__(self, logFile=None, settingsFile=None, notesFile=None):
        """
        Args:
            logFile: path to log file, defaults to None (string)
            settingsFile: path to settings file, defaults to None (string)
            notesFile: path to notes file, defaults to None (string)
        """

        self.logFile = logFile
        self.settingsFile = settingsFile
        self.notesFile = notesFile

        self.trials = []
        self.isLeftLicking = False
        self.isRightLicking = False

        # settings / log parameters
        self.trainer = ""
        self.midSessionTime = ""
        self.dayOfWeek = ""
        self.hintsUsed = False
        self.guaranteedSPlus = True
        self.sequenceType = ""
        self.shrewName = ""
        # contents of notes file, not including automated analysis
        self.notes = ""

        # do reading of settings file
        self.read_settings_file(settingsFile)

        # make first trial
        self.t = TwoAFCTrial(analysis=self)

        # If no logfile, this is a live session -- nothing more to do yet,
        # just wait for process_line calls etc.
        if logFile is None:
            return

        # process log file
        self.read_log_file(logFile)

        # --- pull out some more metadata --- #

        # trainer name, if available
        if notesFile is not None:
            self.read_notes_file(notesFile)

        # shrew name and day of week
        m = re.match("(.*)_(.*)_(\\d+)_log.txt", logFile.split("\\")[-1])
        self.shrewName = m.group(1)
        dateStr = m.group(2)
        (year, month, date) = dateStr.split("-")
        self.date = datetime.date(int(year),int(month),int(date))
        self.session = m.group(3)
        daysOfWeek = ["", "Monday", "Tuesday", "Wednesday", "Thursday",
                      "Friday", "Saturday", "Sunday"]
        self.dayOfWeek = daysOfWeek[self.date.isoweekday()]

        # get time of day at middle of training session, in hh:mm format
        if len(self.trials) > 0:
            t0 = self.trials[0]
            tN = self.trials[-1]
            if len(t0.stateTimes) > 0 and len(tN.stateTimes) > 0:
                tMid = (t0.stateTimes[0] + tN.stateTimes[0]) / 2
                dtMid = datetime.datetime.fromtimestamp(tMid)
                self.midSessionTime = str(dtMid.hour).zfill(2) + ":" + str(dtMid.minute).zfill(2)

        # organize results into summary data for nice plotting
        self.trial_stats()

    def read_notes_file(self, notesFile):
        """
            Args:
                notesFile: path to notes file

            Returns: Nothing

            Scans the notes file looking for the person training

            Depreciated
        """

        if not os.path.isfile(notesFile):
            return

        fileinput.close()  # Close any existing fileinput handles, just in case
        f = fileinput.input(notesFile)
        for line in f:
            if "Theo here!" in line or ": Theo" in line:
                self.trainer = "Theo"
            if "JWS" in line:
                self.trainer = "Joe"
            if "VH" in line or ": Val" in line or "Valerie" in line:
                self.trainer = "Valerie"
            if "CF" in line:
                self.trainer = "Connor"
            if "SF" in line:
                self.trainer = "Susan"
            if "Shrew:" in line or "===" in line:
                # indicates the beginning of automated analysis data;
                # not needed in notes.
                fileinput.close()
                break
            self.notes += line

    def read_settings_file(self, settingsFile):
        """
        Eat a settings file, and thereby gain its powers
        Parses the settings file and sets booleans according to what's in it
        """

        m = re.match("(.*)_(.*)_(\\d+)_settings.txt", settingsFile.split("\\")[-1])
        self.shrewName = m.group(1)

        fileinput.close() # Close any existing fileinput handles, just in case
        for line in fileinput.input(settingsFile):
            toks = line.split(" ")

            if toks[0] == "hintChance":
                if float(toks[2]) == 0:
                    self.hintsUsed = False
                else:
                    self.hintsUsed = True

            if toks[0] == "sLeftPresentations":
                exec("self." + line)

            if toks[0] == "sRightOrientations":
                exec("self." + line)

            if toks[0] == "sLeftOrientations":
                exec("self." + line)

            if toks[0] == "sRightOrientation":
                self.sPlusOrientations = [float(toks[2])]

            if toks[0] == "sequenceType ":
                if "0" in toks[3]:
                    self.sequenceType = "RANDOM"
                if "1" in toks[3]:
                    self.sequenceType = "BLOCK"
                if "2" in toks[3]:
                    self.sequenceType = "RANDOM_RETRY"
                if "3" in toks[3]:
                    self.sequenceType = "BLOCK_RETRY"
                if "4" in toks[3]:
                    self.sequenceType = "SEQUENTIAL"
                if "5" in toks[3]:
                    self.sequenceType = "INTERVAL"
                if "6" in toks[3]:
                    self.sequenceType = "INTERVAL_RETRY"


            if toks[0] == "gratingDuration":
                exec("self." + line)

            if toks[0] == "rewardDuration":
                exec("self." + line)

            if toks[0] == "variableDelayMin":
                exec("self." + line)

            if toks[0] == "variableDelayMax":
                exec("self." + line)

    def read_log_file(self, logFile):
        """
        Args:
            logFile: Path to log file

        Returns: Nothing

        Eat a log file, to absorb its knowledge
        """
        fileinput.close()  # Close any existing fileinput handles, just in case
        for line in fileinput.input(logFile):
            self.process_line(line)

    def process_line(self, line):
        """
        Args:
            line: single line of the log file, pulled from self.read_log_file()

        Returns: Nothing

        Reads a single line of the log. If line represents a timeout state,
        trial is complete.
        """
        self.t.lines.append(line)
        if re.search('State0', line) or re.search('State1', line) or re.search('State2', line):
            self.t.analyze()
            self.trials.append(self.t)
            self.t = TwoAFCTrial(analysis=self)

    def trial_stats(self):
        """
        Call this after data processing to get statistics.
        Makes raw numbers easily accessible.
        Percents will be rounded to the hundredths.
        """

        # inits
        self.nTrials = len(self.trials)
        self.taskLeftErrors = 0
        self.taskRightErrors = 0
        self.taskErrors = 0
        self.taskErrorRate = 0
        self.taskLeftErrorRate = 0
        self.taskRightErrorRate = 0
        self.taskErrorRate = 0
        self.stateLeftFailCounts = {}
        self.stateRightFailCounts = {}

        self.sRightCorrect = 0
        self.sRightResponse = 0  # lick at right port during reward, regardless of stim
        self.sRightTrials = 0    # left-rewarded stim, regardless of shrew's choice
        self.sRightAccuracy = 0
        self.sRightBias = 0
        self.sRightPerformances = {sRightOri : OrientationPerformance() for sRightOri in self.sRightOrientations}  # todo

        self.sLeftCorrect = 0
        self.sLeftResponse = 0
        self.sLeftTrials = 0
        self.sLeftAccuracy = 0
        self.sLeftBias = 0
        self.sLeftPerformances = {sLeftOri : OrientationPerformance() for sLeftOri in self.sLeftOrientations}  # todo

        self.ValidTrials = 0
        self.Correct = 0
        self.Accuracy = 0
        self.ValidRate = 0

        self.totalmL = 0
        self.totalmL_left = 0
        self.totalmL_right = 0
        self.hintmL = 0
        self.hintmL_left = 0
        self.hintmL_right = 0
        self.mLPerHour = 0
        self.trialsPerHour = 0
        self.trainingDuration = 0
        self.meanTimeBetweenTrials = 0

        if self.nTrials == 0:
            return

        # counts of each result type
        self.resultCounts = {r: 0 for r in resultsSet}
        for t in self.trials:
            if t.result is None:
                continue
            self.resultCounts[Results.whatis(t.result)] += 1

        results = self.resultCounts     # shorthand

        # Task error rate
        self.taskLeftErrors = results["TASK_FAIL_LEFT"] + results["NO_RESPONSE_LEFT"]
        self.taskRightErrors = results["TASK_FAIL_RIGHT"] + results["NO_RESPONSE_RIGHT"]
        self.taskLeftErrorRate = round(100*(self.taskLeftErrors / self.nTrials), 2)
        self.taskRightErrorRate = round(100*(self.taskRightErrors / self.nTrials), 2)

        for t in self.trials:   # type TwoAFCTrial
            if t.resultState is None:
                continue
            if t.result == Results.TASK_FAIL_LEFT:
                if States.whatis(t.resultState) in self.stateLeftFailCounts:
                    self.stateLeftFailCounts[States.whatis(t.resultState)] += 1
                else:
                    self.stateLeftFailCounts[States.whatis(t.resultState)] = 1

            if t.result == Results.TASK_FAIL_RIGHT:
                if States.whatis(t.resultState) in self.stateRightFailCounts:
                    self.stateRightFailCounts[States.whatis(t.resultState)] += 1
                else:
                    self.stateRightFailCounts[States.whatis(t.resultState)] = 1

        # Left and right correct trials
        self.sLeftCorrect = results["HIT_LEFT"]
        self.sLeftResponse = results["HIT_LEFT"] + results["MISS_RIGHT"]
        self.sLeftTrials = results["HIT_LEFT"] + results["MISS_LEFT"]

        self.sRightCorrect = results["HIT_RIGHT"]
        self.sRightResponse = results["HIT_RIGHT"] + results["MISS_LEFT"]
        self.sRightTrials = results["HIT_RIGHT"] + results["MISS_RIGHT"]

        # overall correct trials and accuracy
        self.ValidTrials = self.sRightTrials + self.sLeftTrials
        self.ValidRate = round(100*(self.ValidTrials/self.nTrials),2)
        self.Correct = results["HIT_RIGHT"] + results["HIT_LEFT"]

        if self.ValidTrials > 0:
            self.Accuracy = round(100*(self.Correct/self.ValidTrials),2)

        # left and right accuracy
        if self.sRightTrials > 0:
            self.sRightAccuracy = round(100*(self.sRightCorrect / self.sRightTrials), 2)
            self.sRightBias = round(100 * (self.sRightResponse / self.ValidTrials), 2)

        # calculate accuracy and bias
        if self.sLeftTrials > 0:
            self.sLeftAccuracy = round(100*(self.sLeftCorrect / self.sLeftTrials), 2)
            self.sLeftBias = round(100*(self.sLeftResponse / self.ValidTrials), 2)

        # breakdown by orientation
        for t in self.trials:
            sRightOri = t.sRightOrientation
            sLeftOri = t.sLeftOrientation
            if t.numSLeft == max(self.sLeftPresentations) and len(self.sLeftPresentations) > 1:
                # it's an sLeft trial
                if sLeftOri == -1 or sLeftOri not in self.sLeftOrientations:
                    continue
                if t.result == Results.HIT_LEFT:
                    self.sLeftPerformances[sLeftOri].numCorrect += 1
                    self.sLeftPerformances[sLeftOri].numTrials += 1
                elif t.result == Results.MISS_LEFT:
                    self.sLeftPerformances[sLeftOri].numTrials += 1
            else:
                # it's an sPlus trial
                if sRightOri == -1 or sRightOri not in self.sRightOrientations:
                    continue
                if t.result == Results.HIT_RIGHT:
                    self.sRightPerformances[sRightOri].numCorrect += 1
                    self.sRightPerformances[sRightOri].numTrials += 1
                elif t.result == Results.MISS_RIGHT:
                    self.sRightPerformances[sRightOri].numTrials += 1

        # duration
        self.trainingDuration = (self.trials[-1].trialStartTime - self.trials[0].trialStartTime) / 60 / 60
        if self.trainingDuration > 0:
            self.trialsPerHour = len(self.trials) / self.trainingDuration
        else:
            self.trialsPerHour = 0

        # mean time between trials
        for i in range(1, len(self.trials)):
            # compute lost time wasted between each pair of trials
            t = self.trials[i]  # type 2AFCTrial
            s = self.trials[i-1]  # type 2AFCTrial
            if len(t.stateTimes) < 2 or len(s.stateTimes) < 2:
                continue
            sEndTime = s.stateTimes[-1]
            tStartTime = t.stateTimes[1]
            timeBetweenTrials = (tStartTime - sEndTime)
            self.meanTimeBetweenTrials += timeBetweenTrials
        if len(self.trials) >= 2:
            self.meanTimeBetweenTrials /= (len(self.trials) - 1)

        # mL
        for t in self.trials:
            self.totalmL += t.totalmL
            self.hintmL_left += t.hintmL_left
            self.hintmL_right += t.hintmL_right
            self.hintmL += t.hintmL

        if self.trainingDuration > 0:
            self.mLPerHour = self.totalmL / self.trainingDuration
        else:
            self.mLPerHour = 0

    # --- Display Functions --- #
    def str_overview(self):
        """
            Returns: message - string containing human-readable stats to show on UI
        """
        trainTime = seconds_to_human(self.trainingDuration * 60 * 60)
        message = (
            "====" + "\n"
            "Shrew: " + self.shrewName + "\n" + "\n"
            'Accuracy: ' + str(round(self.Accuracy, 2)) + '% (' + str(self.sLeftCorrect+self.sRightCorrect) + '/' +
             str(self.ValidTrials) + ')' + "\n"
            'Valid Trial Rate: ' + str(round(self.ValidRate, 2)) + '% (' + str(self.ValidTrials) + '/' +
             str(self.nTrials) + ')' + "\n" 
            '\nTotal Reward (mL): ' + str(self.totalmL) + "\n")

        if self.hintmL > 0:
            message += "Reward from Hints (mL): " + str(self.hintmL) + " (" + str(round(100*self.hintmL/self.totalmL)) + "% of total)\n\n"

        message += (
            "Run Time: " + trainTime + "\n"
            "Reward Rate (mL/hour): " + str(round(self.mLPerHour, 2)) + "\n"
            "Mean Time Between Trials: " + str(round(self.meanTimeBetweenTrials, 2)) + "s\n"
            "\n"
        )
        return message

    def str_accuracy(self):
        """
            Returns: message - string containing accuracy statistics
            to show on the UI
        """
        nCorrect = self.Correct
        message = (
            '====' + '\n'
            'PERFORMANCE' + "\n"

            "\nOverall Accuracy and Bias:"

            "\nLeft Accuracy: " + str(self.sLeftAccuracy) + "% "
            "(" + str(self.sLeftCorrect) + "/" + str(self.sLeftTrials) + ")"

            "\nLeft Bias: " + str(self.sLeftBias) + "% "
            "(" + str(self.sLeftResponse) + "/" + str(self.ValidTrials) + ")"
            "\n"

            "\nRight Accuracy: " + str(self.sRightAccuracy) + "% "
            "(" + str(self.sRightCorrect) + "/" + str(self.sRightTrials) + ")"

            "\nRight Bias: " + str(self.sRightBias) + "% "
            "(" + str(self.sRightResponse) + "/" + str(self.ValidTrials) + ")"
            "\n"
        )

        message += "\nRight Accuracy by Orientation" + "\n"

        for sRightOrientation in sorted(set(self.sRightOrientations)):
            numCorrect = self.sRightPerformances[sRightOrientation].numCorrect
            numTrials = self.sRightPerformances[sRightOrientation].numTrials

            if numTrials == 0:
                continue

            successRate = numCorrect / numTrials * 100
            successRateStr = str(round(successRate,2))

            oriStr = str(sRightOrientation) + " degrees:"
            oriStr += " " * (17-len(oriStr))
            oriStr += successRateStr + "% (" + str(numCorrect) + "/" + str(numTrials) + ")"
            oriStr += "\n"

            message += oriStr

        message += "\nLeft Accuracy by Orientation" + "\n"

        for sLeftOrientation in sorted(set(self.sLeftOrientations)):
            numCorrect = self.sLeftPerformances[sLeftOrientation].numCorrect
            numTrials = self.sLeftPerformances[sLeftOrientation].numTrials

            if numTrials == 0:
                continue

            successRate = numCorrect / numTrials * 100
            successRateStr = str(round(successRate,2))

            oriStr = str(sLeftOrientation) + " degrees:"
            oriStr += " " * (17-len(oriStr))
            oriStr += successRateStr + "% (" + str(numCorrect) + "/" + str(numTrials) + ")"
            oriStr += "\n"

            message += oriStr

        return message

    def str_task_errors(self):
        """
            Returns: message - string containing error statistics to be presented
            on the UI
        """
        message = (
            '====' + "\n"
            "TASK ERRORS\n" + "\n"
            "Left Task Error Rate: " + str(self.taskLeftErrorRate) + "% (" + str(self.taskLeftErrors)
            + "/" + str(self.nTrials) + ")" + "\n"
            "Right Task Error Rate: " + str(self.taskRightErrorRate) + "% (" + str(self.taskRightErrors)
            + "/" + str(self.nTrials) + ")" + "\n")

        if len(self.stateLeftFailCounts.keys()) > 0:
            message += '\nLeft Task error details: \n'

        for f in self.stateLeftFailCounts:
            message += f + " " + str(self.stateLeftFailCounts[f]) + "\n"

        if self.resultCounts["NO_RESPONSE_LEFT"] > 0:
            message += 'NO_RESPONSE_LEFT ' + str(self.resultCounts["NO_RESPONSE_LEFT"]) + "\n"

        if len(self.stateRightFailCounts.keys()) > 0:
            message += '\nRight Task error details: \n'

        for f in self.stateRightFailCounts:
            message += f + " " + str(self.stateRightFailCounts[f]) + "\n"

        if self.resultCounts["NO_RESPONSE_RIGHT"] > 0:
            message += 'NO_RESPONSE_RIGHT ' + str(self.resultCounts["NO_RESPONSE_RIGHT"]) + "\n"

        message += "\n"
        return message

    def get_results_str(self):
        """
            Calls trials_stats() and then returns the of all processed data to be
            displayed by the UI.

            Returns: string containing output of the str_overview(), str_accuracy()
            and str_task_error() functions
        """
        self.trial_stats()
        return self.str_overview() + self.str_accuracy() + self.str_task_errors()

    def get_summary_path(self):
        """Returns path to summary file using the settings file path as a template"""
        return self.settingsFile.replace("settings", "summary")


@CacheUnlessFilesChanged
def analyzeDir(dirPath):
    """
    Assumes the directory at dirPath contains sets of files including (logFile, settingsFile, notesFile).
    notesFiles are optional but nice.

    Returns a set of Analysis objects, one for each logFile.
    """

    os.chdir(baseDir)
    analyses = []

    for logFile in glob.glob("*log.txt"):

        settingsFile = re.match("(.*)log.txt", logFile).group(1) + "settings.txt"

        m = re.match("(.*)_(.*)_(\\d+)_log.txt", logFile)
        shrewName = m.group(1)
        dateStr = m.group(2)
        notesFile = dateStr + "-notes.txt"
        if not os.path.isfile(baseDir + os.sep + notesFile):
            #sometimes people forget the -notes, so try without that
            notesFile = dateStr + ".txt"
        if not os.path.isfile(baseDir + os.sep + notesFile):
            #sometimes it's _notes instead. Try that too.
            notesFile = dateStr + "_notes.txt"

        print "Log:", logFile, "\nSettings:", settingsFile, "\nNotes:", notesFile
        logFile = baseDir + os.sep + logFile
        settingsFile = baseDir + os.sep + settingsFile
        notesFile = baseDir + os.sep + notesFile

        if not os.path.isfile(settingsFile):
            continue

        a = TwoAFCAnalysis(logFile, settingsFile, notesFile)
        analyses.append(a)

    return analyses


if __name__ == "__main__":
    baseDir = r'C:\Users\theo\Desktop\chico\2014-10-21\0001'
    analyses = analyzeDir(baseDir)
    for a in analyses:  #type: Analysis
        print a.sLeftAccuracy
        print a.sRightAccuracy

from __future__ import division
import sys
sys.path.append("..")


import shelve
import threading

from collections import deque

from db_mixin import DbMixin

from constants.graph_constants import *

from analysis.discrimination_analysis import *

"""
Controls access to performance database files.
"""


class DbPerformance(DbMixin):

    _db = {}
    _lock = threading.Lock()

    def __init__(self):
        pass

    def get_path(self, animalName):
        return DATA_DIR + os.sep + animalName + os.sep + animalName.capitalize() + "_performance.db"

    def add_entry(self, analysis):
        """Make a performance entry out of an analysis object, and add it to the appropriate shrew's DB.
        Will update the entry if it already exists."""
        a = analysis  # type: sd1_analysis.Analysis

        entry = dict()

        #cumulative mL earned
        entry[TOTAL_ML] = []
        mLSoFar = 0
        for t in a.trials:  # type: sd1_analysis.Trial
            mLSoFar += t.totalmL
            entry[TOTAL_ML].append( (t.trialStartTime - a.trials[0].trialStartTime, mLSoFar) )

        # 10-trial average of task errors
        entry[TASK_ERROR_RATE] = []
        lastTenTrials = deque()
        for t in a.trials:  # type: DiscriminationTrial
            if t.result == Results.TASK_FAIL:
                lastTenTrials.append(1)
            else:
                lastTenTrials.append(0)

            if len(lastTenTrials) > 10:
                lastTenTrials.popleft()

            if len(lastTenTrials) == 10:
                errorRate = sum(lastTenTrials) / len(lastTenTrials) * 100
                entry[TASK_ERROR_RATE].append( (t.trialStartTime - a.trials[0].trialStartTime, errorRate) )

        # 10-trial average for discrimination (excludes task-error trials)
        entry[CORRECT_DISCRIMINATION_RATE] = []
        lastTenTrials = deque()
        for t in a.trials:  # type: Trial

            if t.result == Results.HIT or t.result == Results.CORRECT_REJECT:
                lastTenTrials.append(1)
            elif t.result == Results.MISS or t.result == Results.FALSE_ALARM:
                lastTenTrials.append(0)

            if len(lastTenTrials) > 10:
                lastTenTrials.popleft()

            if len(lastTenTrials) == 10:
                correctRate = sum(lastTenTrials) / len(lastTenTrials) * 100
                entry[CORRECT_DISCRIMINATION_RATE].append( (t.trialStartTime - a.trials[0].trialStartTime, correctRate) )

        # (trials x10) per hour
        entry[TRIALS_PER_HOUR] = []
        lastTenTrials = deque()
        for t in a.trials:  # type: sd1_analysis.Trial
            lastTenTrials.append(t.trialStartTime)
            if len(lastTenTrials) > 10:
                lastTenTrials.popleft()
            if len(lastTenTrials) == 10:
                dt = lastTenTrials[-1] - lastTenTrials[0]
                dtInHours = dt/60/60
                trialsPerHour = 10 / dtInHours
                entry[TRIALS_PER_HOUR].append( (t.trialStartTime - a.trials[0].trialStartTime,  trialsPerHour / 10) )  # "tens of trials per hour" is the actual unit

        # add entry to DB
        dateStr = self.get_datestr(a)

        db = self.get(a.shrewName)
        db[dateStr] = entry
        self.sync(a.shrewName)


if __name__ == "__main__":
    cluckerPerformanceDb = DbPerformance().get("Clucker")
    print cluckerPerformanceDb[cluckerPerformanceDb.keys()[0]]



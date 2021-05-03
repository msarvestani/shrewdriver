from __future__ import division
import sys
sys.path.append("..")


import threading

from db_mixin import DbMixin

from constants.graph_constants import *
from analysis.discrimination_analysis import *


class DbEvents(DbMixin):

    _db = {}
    _lock = threading.Lock()

    def get_path(self, animalName):
        return DATA_DIR + os.sep + animalName + os.sep + animalName.capitalize() + "_events.db"

    def add_entry(self, analysis):
        """Make an events entry out of an analysis object, and add it to the appropriate shrew's DB.
        Will update the entry if it already exists."""
        a = analysis  # type: DiscriminationAnalysis

        entry = dict()

        entry[REWARD] = []
        entry[HINT] = []
        entry[STATE] = []
        entry[TAP] = []
        entry[LICK] = []

        for t in a.trials:  # type: DiscriminationTrial
            for (action, timestamp) in zip(t.actionHistory, t.actionTimes):
                dt = timestamp - a.trials[0].stateTimes[0]  # Start counting time from the first trial

                if action == Actions.LICK:
                    entry[LICK].append((dt, 1))
                if action == Actions.LICK_DONE:
                    entry[LICK].append((dt, 0))

                if action == Actions.TAP:
                    entry[TAP].append((dt, 1))
                if action == Actions.TAP_DONE:
                    entry[TAP].append((dt, 0))

            if t.hintTime is not None:
                dt = t.hintTime - a.trials[0].stateTimes[0]
                entry[HINT].append((dt, 1))

            if t.rewardTime is not None:
                dt = t.rewardTime - a.trials[0].stateTimes[0]
                entry[REWARD].append((dt, 1))

            for (state, timestamp) in zip(t.stateHistory, t.stateTimes):
                dt = timestamp - a.trials[0].stateTimes[0]
                entry[STATE].append((dt, state))

            # add entry to DB
            dateStr = self.get_datestr(a)

            db = self.get(a.shrewName)
            db[dateStr] = entry
        self.sync(a.shrewName)

from __future__ import division
import sys
import threading

from db_mixin import DbMixin

sys.path.append("..")

from analysis.discrimination_analysis import *
from constants.graph_constants import *
from constants.task_constants import *


class DbLickTimes(DbMixin):

    _db = {}
    _lock = threading.Lock()

    def get_path(self, animalName):
        return DATA_DIR + os.sep + animalName + os.sep + animalName.capitalize() + "_lick_times.db"

    def add_entry(self, analysis):
        """Make an events entry out of an analysis object, and add it to the appropriate shrew's DB.
        Will update the entry if it already exists."""
        a = analysis  # type: DiscriminationAnalysis

        entry = dict()

        if not hasattr(a, "gratingDuration") \
                or not hasattr(a, "variableDelayMax") \
                or not hasattr(a, "grayDuration"):
            #We won't be able to make lick plots for this session; not sure how long
            #each state was.
            print "missing attrs", hasattr(a, "gratingDuration"), hasattr(a, "variableDelayMax"), hasattr(a, "grayDuration")
            return

        if not hasattr(a, "rewardDuration"):
            # Assumption: reward duration has never been different from gray duration, and could only be shorter.
            # So if unspecified, assume it's the same.
            a.rewardDuration = a.grayDuration

        #read durations out of settings
        entry[STATE_MAX_DURATIONS] = {GRAPH_TIMING_DELAY: a.variableDelayMax,
                                      GRAPH_SMINUS_GRATING: a.gratingDuration,
                                      GRAPH_SPLUS_GRATING: a.gratingDuration,
                                      GRAPH_NON_REWARD: a.grayDuration,
                                      GRAPH_REWARD: a.rewardDuration}

        hasMemoryDelay = False
        if hasattr(a, "sMinusPresentations") and max(a.sMinusPresentations) == 2:
            entry[STATE_MAX_DURATIONS][GRAPH_MEMORY_DELAY] = a.grayDuration
            hasMemoryDelay = True

        #Lick info includes number, state, and time (measured from state start).
        entry[LICK_INFO] = []

        for (trialIndex, t) in enumerate(a.trials):  # type: DiscriminationTrial
            trialNum = trialIndex + 1
            for (action, actionTime) in zip(t.actionHistory, t.actionTimes):
                if action != Actions.LICK:
                    continue

                lickStateName = STATE_TIMEOUT
                lickTimeOffset = 0

                #identify which state the lick happened in
                for (state, stateTime) in zip(t.stateHistory, t.stateTimes):
                    if stateTime > actionTime or state == States.TIMEOUT:
                        break
                    else:
                        lickTimeOffset = actionTime-stateTime
                        lickStateName = stateSet[state]

                # Change state name for display
                if lickStateName == "DELAY":
                    lickStateName = GRAPH_TIMING_DELAY
                elif lickStateName == "SMINUS":
                    lickStateName = GRAPH_SMINUS_GRATING
                elif lickStateName == "SPLUS":
                    lickStateName = GRAPH_SPLUS_GRATING
                elif lickStateName == "REWARD":
                    lickStateName = GRAPH_REWARD
                elif lickStateName == "GRAY":
                    if hasMemoryDelay and t.stateHistory.count(state) == 1:
                        #there was only 1 gray, so it must have been the memory delay.
                        lickStateName = GRAPH_MEMORY_DELAY
                    else:
                        lickStateName = GRAPH_NON_REWARD

                #if the lick happened in a state we care about, add it
                if lickStateName in entry[STATE_MAX_DURATIONS].keys():
                    #print "adding", lickStateName, trialNum
                    entry[LICK_INFO].append( (lickStateName, lickTimeOffset, trialNum) )
                else:
                    #for some reason we got a bad lick; bug? work out later.
                    #print "Can't assign lick to a state in trial", lickStateName, trialNum
                    pass

        # add entry to DB
        dateStr = self.get_datestr(a)
        #if t.result is not None and t.resultState is not None:
            #print dateStr, sd1_analysis.resultsSet[t.result], sd1_analysis.stateSet[t.resultState], trialNum

        db = self.get(a.shrewName)
        db[dateStr] = entry
        self.sync(a.shrewName)




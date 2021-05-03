from __future__ import division
import sys
sys.path.append("..")


import threading
import traceback
from constants.graph_constants import *
from db_mixin import DbMixin
from analysis.discrimination_analysis import *


class DbHistory(DbMixin):

    _db = {}
    _lock = threading.Lock()

    def get_path(self, animalName):
        return DATA_DIR + os.sep + animalName.capitalize() + os.sep + animalName.capitalize() + "_history.db"

    def get_settings(self, animalName, dateStr):
        """Returns the settings associated with a session in dict form.
        Used in calculation of changes."""
        (date, session) = dateStr.split("_")
        sessionShort = str(int(session))  # session filename has no leading zeros, but directory does. (Oops.)
        settingsFile = DATA_DIR + os.sep + animalName + os.sep + date + os.sep + session + os.sep \
            + animalName + "_" + date + "_" + sessionShort + "_settings.txt"

        if not os.path.isfile(settingsFile):
            print "File not found: " + settingsFile
            return None

        settingsDict = {}
        with open(settingsFile, 'r') as f:
            for line in f:
                if "<" in line or '/' in line \
                        or line.startswith("training") \
                        or 'startTimeMillis' in line:
                    #Skip lines that are object definitions, file paths, references to other junk, etc.
                    continue
                if '=' in line:
                    toks = line.split('=')
                    if len(toks) != 2:
                        continue
                    (var, value) = toks
                    var = var.rstrip().lstrip()
                    value = value.rstrip().lstrip()
                    settingsDict[var] = value

        return settingsDict

    def add_entry(self, analysis):
        """Make a history entry out of an analysis object, and add it to the appropriate shrew's DB.
        Will update the entry if it already exists."""
        a = analysis  # type: DiscriminationAnalysis

        entry = dict()

        entry[TASK_ERROR_RATE] = a.taskErrorRate
        entry[CORRECT_DISCRIMINATION_RATE] = a.discriminationPercent
        entry[SPLUS_RESPONSE_RATE] = a.sPlusResponseRate
        entry[SMINUS_REJECT_RATE] = a.sMinusRejectRate

        entry[TOTAL_ML] = a.totalmL
        entry[ML_PER_HOUR] = a.mLPerHour
        entry[NUM_TRIALS] = len(a.trials) / 10
        entry[TRAINING_MINUTES] = a.trainingDuration * 60

        entry[SESSION_START_TIME] = a.trials[0].stateTimes[0]

        #compute changes in settings
        dateStr = self.get_datestr(a)
        changeStr = ""
        db = self.get(a.shrewName)
        db[dateStr] = None

        dateStrs = sorted(db.keys())
        prevDateStr = None
        try:
            if dateStrs.index(dateStr)-1 >= 0:
                prevDateStr = dateStrs[dateStrs.index(dateStr)-1]
        except ValueError:
            traceback.print_exc()

        if prevDateStr is not None:
            currentSettings = self.get_settings(a.shrewName, dateStr)
            prevSettings = self.get_settings(a.shrewName, prevDateStr)

            if currentSettings is not None and prevSettings is not None:
                # check for added or removed settings (very rarely happens)
                newKeys = set(currentSettings.keys()).difference(prevSettings.keys())
                lostKeys = set(prevSettings.keys()).difference(currentSettings.keys())

                for key in newKeys:
                    changeStr += "New setting: " + key + " = " + currentSettings[key] + "\n"

                for key in lostKeys:
                    changeStr += "Removed setting: " + key + "\n"

                # check changes in values for each setting
                commonKeys = set(currentSettings.keys()).intersection(prevSettings.keys())
                for key in commonKeys:
                    if currentSettings[key] == prevSettings[key]:
                        continue
                    else:
                        changeStr += key + " changed from " + prevSettings[key] + " to " + currentSettings[key] + "\n"

        if changeStr != "":
            #add session info at the beginning
            changeStr = "Session " + dateStr + ":\n" + changeStr

        #print "str: ", changeStr
        entry[CHANGES] = changeStr

        # add entry to DB
        db[dateStr] = entry
        self.sync(a.shrewName)




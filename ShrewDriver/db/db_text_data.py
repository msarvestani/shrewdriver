from __future__ import division
import sys
sys.path.append("..")


import threading
import traceback
from constants.graph_constants import *
from db_mixin import DbMixin
from analysis.discrimination_analysis import *


class DbTextData(DbMixin):

    _db = {}
    _lock = threading.Lock()


    def get_path(self, animalName):
        return DATA_DIR + os.sep + animalName.capitalize() + os.sep + animalName.capitalize() + "_text_data.db"


    def add_entry(self, analysis):
        a = analysis  # type: DiscriminationAnalysis
        entry = dict()

        #print "str: ", changeStr
        entry[RESULTS_STR] = a.get_results_str()

        entry[LOG_CONTENTS] = get_logfile_contents(a.logFile)
        entry[SETTINGS_CONTENTS] = get_settings_contents(a.settingsFile)

        dateStr = self.get_datestr(a)
        db = self.get(a.shrewName)
        db[dateStr] = entry
        self.sync(a.shrewName)


def get_logfile_contents(logFile):
    """Just dumps log file, no processing"""
    try:
        with open(logFile, 'r') as fh:
            data = fh.read()
        return data
    except:
        traceback.print_exc()
    return ""

def get_settings_contents(settingsFile):
    """Extracts useful stuff from settings file and returns it"""
    settingsLines = [""]

    junk = ['<', 'training', 'isLicking', 'isTapping', 'shrewEnteredAt', 'stateStartTime', \
             'stateEndTime', 'logFilePath', 'summaryFilePath', 'settingsFilePath', 'lastLickAt',  \
            'lastTapAt', 'state =', 'stateDuration', 'States:', 'arduinoSerial', 'replaceOrientation']
    try:
        fileinput.close()
        for line in fileinput.input(settingsFile):

            #some settings files repeat, so just stop when we've seen something already
            if line in settingsLines:
                fileinput.close()
                break

            #skip lines that aren't relevant.
            lineIsJunk = False
            for j in junk:
                if j in line:
                    lineIsJunk = True
            if lineIsJunk:
                continue

            #this line's good, add it.
            settingsLines.append(line)

        return "".join(settingsLines)
    except:
        traceback.print_exc()
    return ""
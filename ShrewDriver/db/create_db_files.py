from __future__ import division
import sys
import os
import re
import traceback

from db_history import *
from db_performance import *
from db_events import *
from db_lick_times import *
from db_text_data import *
sys.path.append("..")
from analysis.gonogo_analysis import GNGAnalysis


"""
Opens ShrewDriver 1 event logs / settings files.

Produces  output for use with the UI graphs.
"""


def get_session_dirs(shrewDir):
    """Looks in the shrewDir and returns a list containing every session on every training day."""

    allSessionDirs = []
    dateDirs = filter(os.path.isdir, [shrewDir + os.sep + f for f in os.listdir(shrewDir)])
    for dateDir in dateDirs:
        sessionDirs = filter(os.path.isdir, [dateDir + os.sep + f for f in os.listdir(dateDir)])
        allSessionDirs.extend(sessionDirs)

    return allSessionDirs


def get_shrew_dirs():
    shrewDirs = filter(os.path.isdir, [DATA_DIR + os.sep + f for f in os.listdir(DATA_DIR)])
    return shrewDirs


def get_log_and_settings_files(sessionDir):
    logFile = None
    settingsFile = None
    for f in os.listdir(sessionDir):
        filepath = sessionDir+os.sep+f
        if os.path.isfile(filepath) and filepath.endswith("settings.txt"):
            settingsFile = filepath
        if os.path.isfile(filepath) and filepath.endswith("log.txt"):
            logFile = filepath
    return logFile, settingsFile


def get_sessions_for_shrew(shrewName):
    """If db files exist, find out what sessions they have.
    Used for populating dropdown in UI."""
    infile = DATA_DIR + os.sep + shrewName.capitalize() + os.sep + shrewName.capitalize() + "_performance.db"
    shelf = shelve.open(infile)
    sessions = shelf.keys()
    shelf.close()
    return sorted(sessions)


def analyze_dir(sessionDir):
    """Runs analysis on the given dir. Returns None if analysis fails or if there are too few trials."""
    try:
        (logFile, settingsFile) = get_log_and_settings_files(sessionDir)
        if logFile is not None and settingsFile is not None:
            print "analyzing", (logFile, settingsFile)
            a = GNGAnalysis(logFile, settingsFile, None)
            if len(a.trials) < 30:
                print "Skipped - too few trials."
                return None
            return a
    except:
        print("Can't process session " + sessionDir)
        print traceback.print_exc()
        return None


def create_dbs():
    """
    Trawl through all shrew data files
    Produce output files usable by UI graphs
    """

    #analyze all data
    shrewDirs = get_shrew_dirs()
    for shrewDir in shrewDirs:
        sessionDirs = get_session_dirs(shrewDir)

        #analyze all files in that shrew's directory
        analyses = []
        for sessionDir in sessionDirs:
            a = analyze_dir(sessionDir)
            if a is not None:
                analyses.append(a)

        # make database files
        if len(analyses) > 0:
            print "Making dbs for", analyses[0].shrewName
            DbHistory().make(analyses)
            DbPerformance().make(analyses)
            DbLickTimes().make(analyses)
            DbEvents().make(analyses)
            DbTextData().make(analyses)
    print("Done")


def get_datestr_from_session_dir(sessionDir):
    firstPart, sessionStr = os.path.split(sessionDir)
    dateStr = os.path.split(firstPart)[1]
    sessionDateStr = dateStr + '_' + sessionStr
    m = re.search("(\d+).(\d+).(\d+).(\d+)", sessionDateStr)

    try:
        (yearStr, monthStr, dayStr, sessionStr) = m.groups()

        return yearStr.zfill(4) + "-" \
            + monthStr.zfill(2) + "-" \
            + dayStr.zfill(2) + "_" \
            + sessionStr.zfill(4)
    except:
        print("Can't parse session date / number from " + sessionDateStr)
        print traceback.print_exc()
        return None


def update_dbs():
    """
    Go through data files. Analyze and add them to the db if they're not already in there.
    Called by the UI.
    """
    shrewDirs = get_shrew_dirs()
    for shrewDir in shrewDirs:
        animalName = os.path.split(shrewDir)[1].lower()
        dbs = [DbHistory().get(animalName), \
               DbPerformance().get(animalName), \
               DbLickTimes().get(animalName), \
               DbEvents().get(animalName),
               DbTextData().get(animalName)]

        sessionDirs = get_session_dirs(shrewDir)

        sessionsToAdd = []
        for sessionDir in sessionDirs:
            dateStr = get_datestr_from_session_dir(sessionDir)

            #check each db to see if there's an entry for this dateStr
            for db in dbs:
                if dateStr not in db:
                    sessionsToAdd.append(sessionDir)
                    break

        for sessionDir in sessionsToAdd:
            a = analyze_dir(sessionDir)
            if a is not None:
                for db in [DbHistory(), DbPerformance(), DbLickTimes(), DbEvents(), DbTextData()]:
                    db.add_entry(a)
    print("Done")


if __name__ == "__main__":
    update_dbs()

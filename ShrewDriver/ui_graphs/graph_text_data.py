from __future__ import division
import sys
from util.cache import lru_cache
import fileinput
import traceback
sys.path.append("..")

import os

from ui.graph_ui import *
from constants.graph_constants import *
from analysis.gonogo_analysis import GNGAnalysis
from db.db_text_data import *

"""
Would be more efficient to save the analysis, settings, and log file text in a db file
along with the others.
"""

def update_text_data(mainUI):
    mainUI = mainUI  # type: GraphUI

    mainUI.txtResults.setText("Results")
    mainUI.txtSettings.setText("Settings")
    mainUI.txtLogFile.setText("Log File")

    if mainUI is None or not hasattr(mainUI, "selectedAnimal") or mainUI.selectedAnimal is None:
        return

    dbTextData = DbTextData().get(mainUI.selectedAnimal)
    if len(dbTextData.keys()) == 0:
        return

    entry = dbTextData[mainUI.selectedSession]

    #read log and settings files
    mainUI.txtResults.setText(entry[RESULTS_STR])
    mainUI.txtLogFile.setText(entry[LOG_CONTENTS])
    mainUI.txtSettings.setText(entry[SETTINGS_CONTENTS])


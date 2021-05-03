from __future__ import division
import sys
import os
import platform
import datetime
sys.path.append("..")
import pyqtgraph as pg

"""
String constants and colors used across the graphs for 2AFC tasks.
"""

# String constants used in the graphs
CORRECT_DISCRIMINATION_RATE = "Discrimination Rate"
SPLUS_RESPONSE_RATE = "S+ Response Rate"
SMINUS_REJECT_RATE = "S- Reject Rate"
TASK_ERROR_RATE = "Task Error Rate"

TOTAL_ML = "Total mL"
ML_PER_HOUR = "mL / Hour"
NUM_TRIALS = "Trials (x10)"
TRAINING_MINUTES = "Training Time (Minutes)"

TRIALS_PER_HOUR = "Trials (x10) / Hour"

CHANGES = "Changes"
RESULTS_STR = "Results String"
LOG_CONTENTS = "Log Contents"
SETTINGS_CONTENTS = "Settings Contents"

LEFT_LICK = "Left Lick"
RIGHT_LICK = "Right Lick"
CENTER_LICK = "Center Lick"
STATE = "State"
LEFT_HINT = "Left Hint"
RIGHT_HINT = "Right Hint"
LEFT_REWARD = "Left Reward"
RIGHT_REWARD = "Right Reward"
AIR_PUFF = "Air Puff"


SESSION_START_TIME = "Session Start Time"

# These are state descriptions used only in graphing context for now
GRAPH_MEMORY_DELAY = "Memory Delay"
GRAPH_TIMING_DELAY = "Timing Delay"
GRAPH_SMINUS_GRATING = "S- Grating"
GRAPH_SPLUS_GRATING = "S+ Grating"
GRAPH_NON_REWARD = "Non-reward"
GRAPH_REWARD = "Reward"

STATE_MAX_DURATIONS = "State Max Durations"
LICK_INFO = "Lick Info"


# Find the ShrewData dir and assign it to DATA_DIR.
DATA_DIR = os.getcwd()
for i in range(20):
    if os.path.isdir(DATA_DIR + os.sep + "ShrewData"):
        DATA_DIR = DATA_DIR + os.sep + "ShrewData"
        break
    else:
        DATA_DIR += os.sep + ".."
if "ShrewData" not in DATA_DIR:
    # ShrewData dir not found, so just make a dir in the base directory
    if platform.platform().startswith('Windows'):
        DATA_DIR = "C:" + os.sep + "ShrewData"
    else:
        # We're in Linux
        DATA_DIR = os.path.expanduser('~') + os.sep + 'ShrewData'

    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)


def get_color(name):
    """Colors for each name."""

    if name == RIGHT_LICK or name == CHANGES:
        return 0, 255, 0        # green
    elif name == LEFT_LICK or name == CHANGES:
        return 255, 0, 0        # red
    elif name == CENTER_LICK or name == CHANGES:
        return 0, 128, 255      # friendly blue
    elif name == STATE:
        return 128, 128, 128    # gray
    elif name == LEFT_HINT:
        return 255, 255, 0      # yellow
    elif name == RIGHT_HINT:
        return 255, 255, 0      # yellow
    elif name == LEFT_REWARD or name == TOTAL_ML:
        return 0, 128, 255      # friendly blue
    elif name == RIGHT_REWARD or name == TOTAL_ML:
        return 0, 255, 255      # friendly blue
    elif name == CORRECT_DISCRIMINATION_RATE:
        return 0, 255, 255,     # cyan
    elif name == SPLUS_RESPONSE_RATE:
        return 255, 0, 128      # neon pink
    elif name == SMINUS_REJECT_RATE:
        return 255, 0, 255      # magenta
    elif name == TASK_ERROR_RATE:
        return 255, 128, 0      # orange
    elif name == TOTAL_ML:
        return 0, 0, 255        # blue
    elif name == ML_PER_HOUR:
        return 128, 0, 255      # ultramarine or something
    elif name == NUM_TRIALS:
        return 255, 128, 128    # peach
    elif name == TRAINING_MINUTES:
        return 0, 255, 0        # green
    elif name == AIR_PUFF:
        return 255, 149, 195    # kirby colored (because, air puff)
    elif name == CHANGES:
        return 255, 64, 0       # red-ish
    else:
        return 255, 255, 255    # white

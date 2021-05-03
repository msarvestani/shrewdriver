from __future__ import division

import sys
sys.path.append("..")

from constants.task_constants import *

def load_parameters(task):
    print "Using settings for Generic!"

    task.showInteractUI = True  # Enables the interact UI, used in headfixed training.
    # Choose whether a psychopy-generated grating stim or a stim saved as a movie is used
    task.useMovie = False
    task.sPlusDir = 'FIG_Movies/FIG_Movie_'
    task.sMinusDir = 'BG_Movies/BG_Movie_'

    task.screenDistanceMillis = 25
    task.rewardCooldown = 0.5 #If shrew has not licked for this many seconds, make reward available.
    task.rewardBolus = [0, 30, 30, 30, 30, 30, 60]  # Microliters # KM note, braintree pumps cannot dispense less than 10 microliters; do not set below 10
    task.rewardBolus = [60]  # Microliters # KM note, braintree pumps cannot dispense less than 10 microliters; do not set below 10


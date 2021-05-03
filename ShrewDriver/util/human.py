from __future__ import division
import sys
sys.path.append("..")

import math
import random

'''
Contains functions for making data more human-like in formatting.

Time strings, sorting numbers, that kinda stuff.

'''


def seconds_to_human(timeSeconds):
    #returns a human-formatted time string from a number of seconds
    timeHours = math.floor(timeSeconds/60/60)
    if timeHours >= 1:
        timeSeconds -= timeHours*60*60
    timeMinutes = math.floor(timeSeconds/60)
    if timeMinutes >= 1:
        timeSeconds -= timeMinutes*60
    
    timeStr = str(int(timeHours)).zfill(2) + ":"
    timeStr += str(int(timeMinutes)).zfill(2) + ":" + str(int(timeSeconds)).zfill(2)
    return timeStr
    

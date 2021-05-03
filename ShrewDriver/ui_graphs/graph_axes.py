from __future__ import division
import sys
sys.path.append("..")

import datetime
import pyqtgraph as pg


class DateAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            strns.append(timestamp_to_date_string(x))
        return strns

def timestamp_to_date_string(timestamp):
    dateStr = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
    return dateStr



class TimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strns = []
        for x in values:
            strns.append(timestamp_to_string(x))
        return strns

def timestamp_to_string(timestamp):
    timeStr = ''
    hours = int(timestamp / (60*60))
    if hours > 0:
        timestamp = timestamp - hours * (60*60)
        timeStr += str(hours) + ":"

    minutes = int(timestamp / (60))
    if minutes > 0 or hours > 0:
        timestamp = timestamp - minutes * (60)
        timeStr += str(minutes).zfill(2) + ":"

    seconds = int(timestamp)
    if seconds > 0 or minutes > 0 or hours > 0:
        timestamp = timestamp - seconds
        timeStr += str(seconds).zfill(2) + "."

    timeStr += str(int(timestamp*1000)).zfill(3)

    return timeStr

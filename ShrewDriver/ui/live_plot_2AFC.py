# LivePlot_GNG: live_plot.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 19 March 2018

from __future__ import division
import time
import re
import threading
import pyqtgraph as pg
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import QtCore
import numpy as np
import copy
import sys
sys.path.append("..")

from constants.graph_constants_2AFC import *


class LivePlot_2AFC(QWidget):
    
    # define signals that we will accept
    sigEvent = QtCore.pyqtSignal(str, float)
    sigUpdate = QtCore.pyqtSignal()

    def __init__(self, animalName):
        """
        Args:
            animalName: [str] the animal name from ShrewDriver
        """

        self.startTime = time.time()
        self.lastUpdate = 0

        # --- init plot --- #
        self.axis = TimeAxis(orientation='bottom')
        self.app = pg.mkQApp()
        self.vb = pg.ViewBox()
        self.pw = pg.PlotWidget(viewBox=self.vb, axisItems={'bottom': self.axis},
                                enableMenu=False, title="")
        self.pw.showAxis('left', False)
        
        self.pw.setXRange(0, 300)
        self.pw.setYRange(0, 15)
        self.pw.show()
        self.pw.setWindowTitle(animalName + " - Live Plot")
        
        self.pw.addLegend()

        # prevent scaling+scrolling in Y, and don't go into negative x
        self.vb.setLimits(xMin=0, yMin=0, yMax=15, minYRange=15, maxYRange=15)
        self.vb.autoRange()
        
        # --- init plot curves --- #
        numStates = 9
        
        self.leftrewardCurve = IntCurve(LEFT_REWARD, 8, get_color(LEFT_REWARD), 1, self.pw)
        self.rightrewardCurve = IntCurve(RIGHT_REWARD, 7, get_color(RIGHT_REWARD), 1, self.pw)
        self.lefthintCurve = IntCurve(LEFT_HINT, 6, get_color(LEFT_HINT), 1, self.pw)
        self.righthintCurve = IntCurve(RIGHT_HINT, 5, get_color(RIGHT_HINT), 1, self.pw)
        self.stateCurve = IntCurve(STATE, 4, get_color(STATE), numStates, self.pw)
        self.centerlickCurve = IntCurve(CENTER_LICK, 3, get_color(CENTER_LICK), 4, self.pw)
        self.leftlickCurve = IntCurve(LEFT_LICK, 2, get_color(LEFT_LICK), 4, self.pw)
        self.rightlickCurve = IntCurve(RIGHT_LICK, 1, get_color(RIGHT_LICK), 4, self.pw)
        self.airCurve = IntCurve(AIR_PUFF, 0, get_color(AIR_PUFF), 1, self.pw)

        # trailing points needed to represent current state
        self.leftlickState = 0
        self.rightlickState = 0
        self.centerlickState = 0

        QWidget.__init__(self) 
        
        # Accept updates via signals. 
        # We have to do it via the Qt signals and slots system, because
        # we are using two threads, and Qt wants everything in one thread. 
        # So communication between threads must be done via signals, otherwise
        # things get weird (plot updates will be screwed up).
        self.sigEvent.connect(self.add_event)
        self.sigUpdate.connect(self.update)
        
    def add_event(self, eventType, timestamp):
        """
        Process events and update the plot UI.

        Args:
            eventType: [QString] the event type from the Qt slot
            timestamp: [float] timestamp

        Returns: updated plot UI
        """

        # convert from QString
        evtType = str(eventType)
        t = timestamp - self.startTime
        # print "GOT EVENT: " + evtType + " " + str(t)

        if evtType.startswith('CENTERLx'):
            if len(evtType) > 8:
                magnitude = int(evtType[8])
                self.centerlickCurve.append_point(t, magnitude)
            else:
                self.centerlickCurve.append_point(t, 4)
        if evtType == 'CENTERLo':
            self.centerlickCurve.append_point(t, 0)

        if evtType.startswith('LEFTLx'):
            if len(evtType) > 6:
                magnitude = int(evtType[6])
                self.leftlickCurve.append_point(t, magnitude)
            else:
                self.leftlickCurve.append_point(t, 4)
        if evtType == 'LEFTLo':
            self.leftlickCurve.append_point(t, 0)

        if evtType.startswith('RIGHTLx'):
            if len(evtType) > 7:
                magnitude = int(evtType[7])
                self.rightlickCurve.append_point(t, magnitude)
            else:
                self.rightlickCurve.append_point(t, 4)
        if evtType == 'RIGHTLo':
            self.rightlickCurve.append_point(t, 0)

        if evtType.startswith('State'):
            stateNumber = int(evtType[5:])
            self.stateCurve.append_point(t, stateNumber)
        if evtType == 'Puff':
            self.airCurve.append_point(t, 1)
            self.airCurve.append_point(t + 0.001, 0)
        if evtType == 'LeftRL':
            self.lefthintCurve.append_point(t, 1)
            self.lefthintCurve.append_point(t + 0.001, 0)
        if evtType == 'RightRL':
            self.righthintCurve.append_point(t, 1)
            self.righthintCurve.append_point(t + 0.001, 0)
        if evtType == 'LeftRH':
            self.leftrewardCurve.append_point(t, 1)
            self.leftrewardCurve.append_point(t + 0.001, 0)
        if evtType == 'RightRH':
            self.rightrewardCurve.append_point(t, 1)
            self.rightrewardCurve.append_point(t + 0.001, 0)

        # ignore any other events
        super(LivePlot_2AFC, self).repaint()

    def update(self, t=None):
        """Called periodically from training program. Updates each curve to
        show current state.
        Args:
            t: [float] parameter is only used by test function below.
        """

        if t is None:
            # t is only defined for testing examples; normally it's the current time.
            t = time.time() - self.startTime
        if t - self.lastUpdate < 1:
            # update every 1s at most
            return

        self.lastUpdate = t
        for curve in [self.leftlickCurve, self.rightlickCurve, self.stateCurve,
                      self.airCurve, self.leftrewardCurve,
                      self.rightrewardCurve, self.lefthintCurve,
                      self.righthintCurve]:
            curve.update(t)
        # self.repaint()
        super(LivePlot_2AFC, self).repaint()
        
    def add_test_points(self):
        """This is a function for testing the plots."""

        self.startTime = 0
        self.add_event("LEFTLx", 100)
        self.add_event("LEFTLo", 130)
        self.add_event("LEFTLx", 500)
        self.add_event("LEFTLo", 530)
        self.add_event("LEFTLx", 800)
        self.add_event("LEFTLo", 830)
        self.add_event("Puff", 200)
        self.add_event("Puff", 650)
        self.add_event("Puff", 1200)
        self.add_event("Puff", 2650)
        self.add_event("RIGHTLx", 200)
        self.add_event("RIGHTLo", 220)
        self.add_event("RIGHTLx", 1200)
        self.add_event("RIGHTLo", 1220)
        self.add_event("RIGHTLx", 1240)
        self.add_event("RIGHTLo", 1280)
        self.add_event("State0", 0)
        self.add_event("State1", 500)
        self.add_event("State2", 1000)
        self.add_event("State3", 1500)
        self.add_event("State4", 2000)
        self.add_event("State5", 2500)
        self.add_event("State6", 3000)
        self.add_event("State7", 3500)
        self.add_event("State0", 4000)
        self.add_event("RL", 650)
        self.add_event("RL", 1650)
        self.add_event("RL", 3650)
        self.add_event("LeftRH", 700)
        self.add_event("RightRH", 2700)

        self.update(t=5000)


class IntCurve:
    def __init__(self, name, index, color, yMax, pw):
        """
        Args:
            name: [int] the handle for the curve
            index: [int] index for the trace we want to manipulate
            color: [Qt variable] trace color assigned by the name
            yMax: [int] may Y range
            pw: [Qt object] Qt PLot Widget
        """

        self.name = name
        # specifies where the curve is vertically on the plot
        self.yMin = index * 1.1
        # yMax is the highest input value.
        self.yMax = yMax

        self.x = [0]
        self.xBase = [0]
        self.y = [self.yMin]
        self.yBase = [self.yMin]

        self.state = 0
        
        self.yPrev = 0
        self.xPrev = 0
        
        # make curve on plotwidget 'pw'
        self.sig = pw.plot(pen=color, name=self.name)
        self.sig.setData(self.x, self.y)
        self.base = pw.plot(pen=color)
        self.base.setData(self.xBase,self.yBase)
        fill = pg.FillBetweenItem(self.base, self.sig, color)
        pw.addItem(fill)
    
    def append_point(self, xNew, yNew):
        """
        Display the latest point associated with this curve.

        Args:
            xNew: [float] new X position
            yNew: [float] new Y position
        """

        # add two points to make vertical line on curve
        # (low-to-high or high-to-low)
        self.x.append(xNew)
        self.y.append(self.yPrev/self.yMax + self.yMin)
        self.x.append(xNew)
        self.y.append(yNew/self.yMax + self.yMin)
        
        # update base curve as well
        self.xBase.append(xNew)
        self.yBase.append(self.yMin)

        # save input point so we can interpret the next input
        self.xPrev = xNew
        self.yPrev = yNew

        # update drawn lines with new data
        self.sig.setData(self.x, self.y)
        self.base.setData(self.xBase, self.yBase)

    def update(self, t):
        """Called periodically with no event. Just updates this curve to
        show current state.

        Args:
            t: [float] time
        """

        # add current state to a temporary point array
        self.xRender = copy.copy(self.x)
        self.xRenderBase = copy.copy(self.xBase)
        self.yRender = copy.copy(self.y)
        self.yRenderBase = copy.copy(self.yBase)

        self.xRender.append(t)
        self.xRenderBase.append(t)
        self.yRender.append(self.yPrev/self.yMax + self.yMin)
        self.yRenderBase.append(self.yMin)

        # render it
        self.sig.setData(self.xRender, self.yRender)
        self.base.setData(self.xRenderBase, self.yRenderBase)


def timestamp_to_string(timestamp):
    """
    Converts timestamps to strings

    Args:
        timestamp: [float]
    """

    timeStr = ''
    hours = int(timestamp / (60*60))
    if hours > 0:
        timestamp = timestamp - hours * (60*60)
        timeStr += str(hours) + ":"
    
    minutes = int(timestamp / 60)
    if minutes > 0 or hours > 0:
        timestamp = timestamp - minutes * 60
        timeStr += str(minutes).zfill(2) + ":"
    
    seconds = int(timestamp)
    if seconds > 0 or minutes > 0 or hours > 0:
        timestamp = timestamp - seconds
        timeStr += str(seconds).zfill(2) + "."
    
    timeStr += str(int(timestamp*1000)).zfill(3)
    
    return timeStr


class TimeAxis(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        """
        Args:
            values: [float]
            scale: [float]
            spacing: [float]

        Returns: list of most recent timestamps converted to strings
        """

        strns = []
        for x in values:
            strns.append(timestamp_to_string(x))
        return strns


if __name__ == '__main__':
    from pyqtgraph.Qt import QtGui, QtCore
    app = QtGui.QApplication(sys.argv)
    lp = LivePlot_2AFC('AnimalName')
    lp.add_test_points()
    QtGui.QApplication.instance().exec_()

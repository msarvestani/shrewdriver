from __future__ import division
import sys
sys.path.append("..")


import time
import random
import numpy as np

from PyQt4 import QtCore, QtGui, uic
import pyqtgraph as pg

from db.db_lick_times import *
from graph_axes import *
from constants.graph_constants import *
from graph_curves import *


class LickPlot():

    """
    There are multiple plots on the Lick Times display.
    This class contains the plot instance and data for a plot.
    """

    BIN_SIZE = 0.1

    def __init__(self, graphLickTimes, stateName, maxDuration):
        self.glt = graphLickTimes  # type:GraphLickTimes
        self.stateName = stateName
        self.maxDuration = maxDuration

        self.plot = self.glt.gw.addPlot(name=stateName, title=stateName)  # type: pg.PlotItem
        self.vb = self.plot.getViewBox()
        self.yMax = 1

        #data
        self.lickTimes = []
        self.trialNums = []

        #curves -- we will show one of these at a time using setData
        self.curveTrials = pg.PlotDataItem([], [], pen=None, symbol='o', symbolSize=5, symbolPen=(255,0,0,200), symbolBrush=(255,255,255,255))
        self.curveHistogram = pg.PlotCurveItem([0], [], stepMode=True, fillLevel=0, brush=(0, 0, 255, 80), pen=(255,0,0,200))

    def add_point(self, lickTime, trialNum):
        self.lickTimes.append(lickTime)
        self.trialNums.append(trialNum)

    def set_histogram_ymax(self, yMax):
        # All plots should have the same y-axis when displaying histograms,
        # otherwise it's visually misleading. This function allows GraphLickTimes to coordinate
        # yMax between the different plots.
        self.yMax = yMax
        self.vb.setLimits(xMin=0, xMax=self.maxDuration, yMin=0, yMax=self.yMax,
                          minXRange=self.maxDuration, maxXRange=self.maxDuration,
                          minYRange=self.yMax, maxYRange=self.yMax)

    def update(self):
        self.plot.removeItem(self.curveHistogram)
        self.plot.removeItem(self.curveTrials)
        if self.glt.curveToShow == self.glt.TYPE_HISTOGRAM:
            #if showing as histogram, recompute it

            binEndpoints = np.arange(0, self.maxDuration+self.BIN_SIZE, self.BIN_SIZE)
            y, x = np.histogram(self.lickTimes, bins=binEndpoints)

            #show only histogram curve
            self.curveHistogram.setData(x, y)
            self.plot.addItem(self.curveHistogram)

            #change y-axis height
            self.yMax = 1
            if len(y) > 0:
                self.yMax = max(y)
            self.vb.setLimits(xMin=0, xMax=self.maxDuration, yMin=0, yMax=self.yMax,
                              minXRange=self.maxDuration, maxXRange=self.maxDuration,
                              minYRange=self.yMax, maxYRange=self.yMax)

        else:
            #show only points curve
            self.curveTrials.setData(self.lickTimes, self.trialNums)
            self.plot.addItem(self.curveTrials)

            #change y-axis height
            self.yMax = 1
            if len(self.trialNums) > 0:
                self.yMax = max(self.trialNums)
            self.vb.setLimits(xMin=0, xMax=self.maxDuration, yMin=0, yMax=self.yMax,
                              minXRange=self.maxDuration, maxXRange=self.maxDuration,
                              minYRange=self.yMax, maxYRange=self.yMax)

class GraphLickTimes():
    """
    A collection of LickPlot items, one for each state. Shows when the shrew licked.
    Can display as histogram or points by trial number.
    Needs to know how long each state can last (stateMaxDurations).
    """

    TYPE_HISTOGRAM = "Histogram"
    TYPE_POINTS = "Points"
    PLOT_ORDER = [GRAPH_TIMING_DELAY, GRAPH_MEMORY_DELAY, GRAPH_SMINUS_GRATING, GRAPH_NON_REWARD, GRAPH_SPLUS_GRATING, GRAPH_REWARD]

    def __init__(self, mainUI):
        self.mainUI = mainUI  # type: main_ui.MainUI
        self.gw = pg.GraphicsLayoutWidget()
        self.gw.setLayout(QtGui.QGridLayout())
        self.plots = {}
        self.curveToShow = self.TYPE_HISTOGRAM
        self.stateMaxDurations = {}

        self.placeholderPlot = None

    def set_curve_type(self, curveToShow):
        # curve type is set by UI and can be TYPE_POINTS or TYPE_HISTOGRAM.
        self.curveToShow = curveToShow

    def add_plot(self, stateName, maxDuration):
        lickPlot = LickPlot(self, stateName, maxDuration)
        self.plots[stateName] = lickPlot


    def clear_plots(self):
        for stateName in self.plots.keys():
            self.gw.removeItem(self.plots[stateName].plot)
        self.plots = {}

        self.mainUI.lickPlotFrameLayout.removeWidget(self.gw)
        self.gw = pg.GraphicsLayoutWidget()
        self.mainUI.lickPlotFrameLayout.addWidget(self.gw)


    def make_plots(self):
        """Create a plot for each state."""
        #remove existing plots
        self.clear_plots()

        for state in self.PLOT_ORDER:
            if state in self.stateMaxDurations.keys():
                self.add_plot(state, self.stateMaxDurations[state])

    def add_point(self, stateName, lickTime, trialNum):
        if stateName not in self.plots.keys():
            print "Error: No plot for state ", stateName
        self.plots[stateName].add_point(lickTime, trialNum)

    def update(self):
        for stateName in self.plots.keys():
            self.plots[stateName].update()
        self.update_y_axes()

    def update_y_axes(self):
        if self.mainUI.rdoHistogram.isChecked():
            # make it so all plots have the same y-axis height
            yMax = 0
            for stateName in self.plots.keys():
                if self.plots[stateName].yMax > yMax:
                    yMax = self.plots[stateName].yMax
            for stateName in self.plots.keys():
                self.plots[stateName].set_histogram_ymax(yMax)


    def update_checked(self):
        # histogram / points display
        if self.mainUI.rdoHistogram.isChecked():
            self.curveToShow = self.TYPE_HISTOGRAM
        elif self.mainUI.rdoTrialNumber.isChecked():
            self.curveToShow = self.TYPE_POINTS

        # tell plots to update
        for stateName in self.plots:
            self.plots[stateName].update()
        self.update_y_axes()


    def load_db(self):
        # pull data from database file, if available
        if self.mainUI is None \
                or not hasattr(self.mainUI, "selectedAnimal") \
                or self.mainUI.selectedAnimal is None\
                or not hasattr(self.mainUI, "selectedSession") \
                or self.mainUI.selectedSession is None:
            return

        shrewName = self.mainUI.selectedAnimal
        dbLickTimes = DbLickTimes().get(shrewName)
        if len(dbLickTimes.keys()) == 0:
            return

        session = self.mainUI.selectedSession
        if session not in dbLickTimes:
            print session, "not in", dbLickTimes.keys()
            return
        sessionData = dbLickTimes[session]

        if not STATE_MAX_DURATIONS in sessionData:
            print "missing", STATE_MAX_DURATIONS, "in session", session
            return
        if not LICK_INFO in sessionData:
            print "missing", LICK_INFO, "in session", session
            return

        self.stateMaxDurations = sessionData[STATE_MAX_DURATIONS]
        self.make_plots()

        for lickPoint in sessionData[LICK_INFO]:
            (stateName, lickTime, trialNum) = lickPoint
            self.add_point(stateName, lickTime, trialNum)
        self.update()

def add_test_points(glt):

    stateNames = [GRAPH_TIMING_DELAY, GRAPH_SMINUS_GRATING, GRAPH_SPLUS_GRATING, GRAPH_MEMORY_DELAY, GRAPH_NON_REWARD, GRAPH_REWARD]
    maxDurations = [1.5, 0.5, 0.5, 1.0, 1.0, 1.0]

    stateMaxDurations = dict(zip(stateNames, maxDurations))
    glt.set_plots(stateMaxDurations)

    n = 400
    for trialNum in range(n):
        stateName = random.choice(stateNames)
        maxDuration = stateMaxDurations[stateName]
        lickTime = random.random()*maxDuration
        glt.add_point(stateName, lickTime)
    glt.update()

if __name__ == "__main__":
    # make an application for the sensor graph
    app = QtGui.QApplication(sys.argv)
    mw = QtGui.QMainWindow()

    glt = GraphLickTimes(None)
    add_test_points(glt)
    mw.setCentralWidget(glt.plot)

    mw.setGeometry(200, 200, 800, 600)

    mw.show()
    app.exec_()

from __future__ import division
import sys
sys.path.append("..")


import time
import threading
from collections import OrderedDict

from PyQt4 import QtCore, QtGui, uic
import pyqtgraph as pg

from db.db_events import *
from graph_axes import *
from graph_curves import *
from constants.graph_constants import *

class Event():

    def __init__(self):
        self.type = ""  # string, such as LICK, TAP, STATE
        self.value = 0  # number. 0 for off, 1 for on, state can be anything
        self.timestamp = 0  # in seconds since start

class GraphEvents():
    """
    Displays licks, taps, behavior state changes, rewards, and hints in real time.
    Can be used to show historical events data from previous sessions.
    """

    def __init__(self, mainUI):
        self.mainUI = mainUI  # type: main_ui.MainUI

        #--- init plot ---#
        self.vb = pg.ViewBox()
        self.axis = TimeAxis(orientation='bottom')
        self.plot = pg.PlotWidget(viewBox=self.vb, axisItems={'bottom': self.axis}, enableMenu=False, title="")
        self.legend = self.plot.addLegend()

        self.plot.showAxis('left', False)

        self.plot.setXRange(0, 300)
        self.plot.setYRange(0, 10)

        # prevent scaling+scrolling in Y, and don't go into negative x
        self.vb.setLimits(xMin=0, yMin=0, yMax=10, minYRange=10, maxYRange=10)
        self.vb.autoRange()

        #--- init plot curves ---#
        numStates = 7
        self.curves = {}
        self.curves[REWARD] = IntCurve(REWARD, 4, get_color(REWARD), 1, self.plot)
        self.curves[HINT] = IntCurve(HINT, 3, get_color(HINT), 1, self.plot)
        self.curves[STATE] = IntCurve(STATE, 2, get_color(STATE), numStates, self.plot)
        self.curves[LICK] = IntCurve(LICK, 1, get_color(LICK), 1, self.plot)
        self.curves[TAP] = IntCurve(TAP, 0, get_color(TAP), 1, self.plot)

        # update timer
        self.timer = None
        self.startTime = 0

    def start(self):
        # Start update timer
        self.startTime = time.time()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000)

    def stop(self):
        if self.timer is not None:
            self.timer.stop()

    def update(self):
        """Called periodically by timer."""
        t = time.time()-self.startTime
        for curveName in self.curves.keys():
            self.curves[curveName].update(t)


    def add_point(self, curveName, timestamp, value):
        #print "GOT EVENT: " + curveName + " " + str(timestamp)
        if curveName in self.curves:
            self.curves[curveName].add_data(timestamp, value)
            if curveName == REWARD or curveName == HINT:
                #hints and rewards are just instantaneous spikes, so add a 0-point following them
                self.curves[curveName].add_data(t+0.01,0)
        else:
            print "invalid curve:", curveName


    def load_db(self):
        # pull data from database file, if available
        self.clear_curves()

        if self.mainUI is None \
                or not hasattr(self.mainUI, "selectedAnimal") \
                or self.mainUI.selectedAnimal is None\
                or not hasattr(self.mainUI, "selectedSession") \
                or self.mainUI.selectedSession is None:
            return

        shrewName = self.mainUI.selectedAnimal

        dbEvents = DbEvents().get(shrewName)
        if len(dbEvents.keys()) == 0:
            return

        session = self.mainUI.selectedSession
        if session not in dbEvents:
            #print session, " not in ", shelf.keys()
            return
        sessionData = dbEvents[session]

        for cn in sessionData.keys():
            if cn in self.curves:
                pointList = sessionData[cn] #each curve entry is an (x, y) tuple already.
                if not isinstance(pointList, list):
                    print shrewName, session, cn, pointList
                    continue
                for (x, y) in pointList:
                    self.curves[cn].add_data(x, y)
                    if cn == REWARD or cn == HINT:
                        #hints and rewards are just instantaneous spikes, so add a 0-point following them
                        self.curves[cn].add_data(x+0.01, 0)


        for cn in self.curves:
            self.curves[cn].update()


    def clear_curves(self):
        for cn in self.curves:
            self.curves[cn].clear()

def add_test_points(ge):
    ge.startTime = time.time()
    ge.add_point(LICK, ge.startTime+100, 1)
    ge.add_point(LICK, ge.startTime+130, 0)
    ge.add_point(LICK, ge.startTime+500, 1)
    ge.add_point(LICK, ge.startTime+530, 0)
    ge.add_point(LICK, ge.startTime+800, 1)
    ge.add_point(LICK, ge.startTime+830, 0)
    ge.add_point(TAP, ge.startTime+200, 1)
    ge.add_point(TAP, ge.startTime+220, 0)
    ge.add_point(TAP, ge.startTime+1200, 1)
    ge.add_point(TAP, ge.startTime+1220, 0)
    ge.add_point(TAP, ge.startTime+1240, 1)
    ge.add_point(TAP, ge.startTime+1280, 0)
    ge.add_point(STATE, ge.startTime+0, 0)
    ge.add_point(STATE, ge.startTime+500, 1)
    ge.add_point(STATE, ge.startTime+1000, 2)
    ge.add_point(STATE, ge.startTime+1500, 3)
    ge.add_point(STATE, ge.startTime+2000, 4)
    ge.add_point(STATE, ge.startTime+2500, 5)
    ge.add_point(STATE, ge.startTime+3000, 7)
    ge.add_point(STATE, ge.startTime+3500, 1)
    ge.add_point(STATE, ge.startTime+4000, 0)
    ge.add_point(HINT, ge.startTime+650, 1)
    ge.add_point(HINT, ge.startTime+1650, 1)
    ge.add_point(HINT, ge.startTime+3650, 1)
    ge.add_point(REWARD, ge.startTime+700, 1)
    ge.add_point(REWARD, ge.startTime+2700, 1)

if __name__ == "__main__":
    # make an application for the events graph
    app = QtGui.QApplication(sys.argv)

    ge = GraphEvents(None)
    add_test_points(ge)

    mw = QtGui.QMainWindow()
    mw.setCentralWidget(ge.plot)

    mw.setGeometry(200, 200, 800, 600)

    mw.show()
    app.exec_()


from __future__ import division
import sys
sys.path.append("..")


import time
import os
import shelve
import re

from PyQt4 import QtCore, QtGui, uic
import pyqtgraph as pg

from graph_axes import *
from constants.graph_constants import *
from graph_curves import *
import random
import copy


sys.path.append("..")
from db.db_history import DbHistory

class GraphHistory():
    """
    For a given shrew, show many historical performance statistics.
    One data point represents a whole training session.
    """

    #height of the "changes" dots
    CHANGES_Y_POS = 4

    def __init__(self, mainUI):
        self.mainUI = mainUI  # type: main_ui.MainUI
        self.displayedAnimal = self.mainUI.selectedAnimal
        self.plot = pg.PlotWidget()

        #--- init plot ---#
        self.vb = pg.ViewBox()
        self.axis = DateAxis(orientation='bottom')
        self.plot = pg.PlotWidget(viewBox=self.vb, axisItems={'bottom': self.axis}, enableMenu=False, title="")
        self.legend = self.plot.plotItem.addLegend(offset=(900,10))

        thirtyDays = 30*24*60*60
        self.plot.setXRange(time.time()-thirtyDays, time.time()) #Default range: the last 30 days
        self.plot.setYRange(0, 100)

        #limit scaling+scrolling in Y, and don't go into negative x
        self.vb.setLimits(xMin=0, yMin=0, yMax=200, minYRange=200, maxYRange=200)

        self.curves = {}
        curveNames = [CORRECT_DISCRIMINATION_RATE,
                      SPLUS_RESPONSE_RATE,
                      SMINUS_REJECT_RATE,
                      TASK_ERROR_RATE,
                      TOTAL_ML,
                      ML_PER_HOUR,
                      NUM_TRIALS,
                      TRAINING_MINUTES
                      ]
        for i, cn in enumerate(curveNames):
            self.curves[cn] = LineDotCurve(self.plot, cn)

        #Make a curve to show changes in training parameters.
        self.changeBrushColor = get_color("Changes") + (128,)
        self.changePenColor = get_color("Changes") + (255,)
        self.changeCurve = pg.ScatterPlotItem(size=12,
                                              name="Changes",
                                              brush=pg.mkBrush(self.changeBrushColor),
                                              pen=pg.mkPen(self.changePenColor))
        self.plot.addItem(self.changeCurve)
        self.legend.addItem(self.changeCurve, name="Changes")

        self.changeCurve.sigClicked.connect(self.change_clicked) #when a change point gets clicked, call this function

        #start
        if self.mainUI is not None:
            self.update_checked()
            self.load_db()

    def load_db(self):
        """ Loads data from db and refreshes graph display """
        if self.displayedAnimal == self.mainUI.selectedAnimal:
            #animal didn't change, probably just the session. Don't need to do anything.
            return
        self.displayedAnimal = self.mainUI.selectedAnimal

        self.clear_curves()

        if self.mainUI is None or not hasattr(self.mainUI, "selectedAnimal") or self.mainUI.selectedAnimal is None:
            return

        shrewName = self.mainUI.selectedAnimal
        dbHistory = DbHistory().get(shrewName)
        if len(dbHistory.keys()) == 0:
            return

        dateSessions = sorted(dbHistory.keys())
        for dateSession in dateSessions:
            sessionData = dbHistory[dateSession]
            if sessionData is None:
                continue
            for cn in sessionData.keys():
                if cn in self.curves and SESSION_START_TIME in sessionData:
                    self.curves[cn].add_data(float(sessionData[SESSION_START_TIME]), float(sessionData[cn]))

            if CHANGES in sessionData.keys() and SESSION_START_TIME in sessionData:
                if sessionData[CHANGES] != "":
                    self.add_change_point(float(sessionData[SESSION_START_TIME]), copy.copy(sessionData[CHANGES]))

        for cn in self.curves:
            self.curves[cn].update()

        self.changeCurve.update()


        #When data is loaded, set x-axis range to show relevant dates.
        #Bit of a pain to get a timestamp from a date, need to subtract seconds from 1970.
        m = re.match("(\d+)-(\d+)-(\d+)_(\d+)", dateSessions[-1])
        (year, month, day) = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
        lastSessionDate = datetime.datetime(year, month, day)
        epoch = epoch = datetime.datetime(1970, 1, 1, 0, 0, 0)
        lastSessionTime = (lastSessionDate - epoch).total_seconds() + 3*24*60*60 #leave 3-day space at the end
        thirtyDays = 30*24*60*60
        self.plot.setXRange(lastSessionTime - thirtyDays, lastSessionTime) #Default range: the last 30 days

    def clear_curves(self):
        for cn in self.curves:
            self.curves[cn].clear()
        self.changeCurve.clear()

    def add_point(self, curveName, x, y, data=""):
        self.curves[curveName].add_data(x,y,data)

    def add_change_point(self, timestamp, data):
        scatterPoint = [{'pos': (timestamp, self.CHANGES_Y_POS),
                          'data': data}]
        self.changeCurve.addPoints(scatterPoint)

    def hide_curve(self, curveName):
        self.curves[curveName].hide()

    def show_curve(self, curveName):
        self.curves[curveName].show()


    def update_checked(self):
        #hide all curves
        self.legend.scene().removeItem(self.legend)
        for cn in self.curves:
            self.hide_curve(cn)

        #show just the relevant ones
        self.legend = self.plot.plotItem.addLegend(offset=(900,10))
        self.legend.addItem(self.changeCurve, name=CHANGES)

        namesToShow = []
        if self.mainUI.chkDiscriminationRateHist.isChecked():
            namesToShow.append(CORRECT_DISCRIMINATION_RATE)
        if self.mainUI.chkSPlusResponseRateHist.isChecked():
            namesToShow.append(SPLUS_RESPONSE_RATE)
        if self.mainUI.chkSMinusRejectRateHist.isChecked():
            namesToShow.append(SMINUS_REJECT_RATE)
        if self.mainUI.chkTaskErrorRateHist.isChecked():
            namesToShow.append(TASK_ERROR_RATE)

        if self.mainUI.chkTotalmLHist.isChecked():
            namesToShow.append(TOTAL_ML)
        if self.mainUI.chkmLPerHourHist.isChecked():
            namesToShow.append(ML_PER_HOUR)
        if self.mainUI.chkTrialsHist.isChecked():
            namesToShow.append(NUM_TRIALS)
        if self.mainUI.chkTrainingDurationHist.isChecked():
            namesToShow.append(TRAINING_MINUTES)

        if TRAINING_MINUTES in namesToShow:
            self.vb.setLimits(xMin=0, yMin=0, yMax=200, minYRange=200, maxYRange=200)
        else:
            self.vb.setLimits(xMin=0, yMin=0, yMax=100, minYRange=100, maxYRange=100)

        for cn in namesToShow:
            self.curves[cn].show()
            self.legend.addItem(self.curves[cn].lineCurve, name=cn)
        self.changeCurve.show()


    def change_clicked(self, plot, points):
        #reset pen on existing points
        outline = pg.mkPen(get_color(CHANGES) + (255,))
        for p in plot.points():
            p.setPen(outline)

        #highlight clicked point
        if len(points) > 0:
            points[0].setPen('w', width=2)
            print "\n" + points[0].data()

            #set to selected session
            lines = points[0].data().split("\n")
            for line in lines:
                if 'Session' in line:
                    m = re.search("\ (.*):", line)
                    sessionStr = m.groups()[0]
                    self.mainUI.set_combo_box(self.mainUI.cmbSession, sessionStr)
                    break

def add_test_points(gh):
    n = 20
    secondsPerDay = 60*60*24
    for i in range(n):
        t = time.time() - i*secondsPerDay
        gh.add_point(CORRECT_DISCRIMINATION_RATE, t, random.random()*100)
        gh.add_point(SPLUS_RESPONSE_RATE, t, random.random()*50)
        gh.add_point(SMINUS_REJECT_RATE, t, random.random()*30)
        gh.add_point(TASK_ERROR_RATE, t, random.random()*20+50)
        gh.add_point(TOTAL_ML, t, random.random()*100)
        gh.add_point(ML_PER_HOUR, t, random.random()*50)
        gh.add_point(NUM_TRIALS, t, random.random()*30)
        gh.add_point(TRAINING_MINUTES, t, random.random()*20+50)

    for i in range(n):
        #add "changed" points to some arbitrary days
        t = time.time() - i*secondsPerDay
        if i % 5 == 1 or i % 7 == 1:
            gh.add_change_point(t, str(i*6) + "yo")


if __name__ == "__main__":
    # make an application for the sensor graph
    app = QtGui.QApplication(sys.argv)
    gh = GraphHistory(None)
    add_test_points(gh)

    mw = QtGui.QMainWindow()
    mw.setCentralWidget(gh.plot)

    mw.setGeometry(200, 200, 800, 600)

    mw.show()
    app.exec_()

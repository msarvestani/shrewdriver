from __future__ import division
import sys
sys.path.append("..")

import shelve

from PyQt4 import QtCore, QtGui, uic
import pyqtgraph as pg

from db.db_performance import *
from graph_axes import *
from constants.graph_constants import *
from graph_curves import *
import random
import time

class GraphPerformance():
    """
    Displays a rolling average of discrimination performance, task errors, and reward rate over trials.
    """

    def __init__(self, mainUI):
        self.mainUI = mainUI  # type: main_ui.MainUI
        self.plot = pg.PlotWidget()

        #--- init plot ---#
        self.vb = pg.ViewBox()
        self.axis = TimeAxis(orientation='bottom')
        self.plot = pg.PlotWidget(viewBox=self.vb, axisItems={'bottom': self.axis}, enableMenu=False, title="")
        self.legend = self.plot.plotItem.addLegend()

        self.plot.setXRange(0, 60*60)  # 1 hour of data (typical)
        self.plot.setYRange(0, 100)

        #limit scaling+scrolling in Y, and don't go into negative x
        self.vb.setLimits(xMin=0, yMin=0, yMax=100, minYRange=100, maxYRange=100)

        self.curves = {}
        curveNames = [CORRECT_DISCRIMINATION_RATE,
                      TASK_ERROR_RATE,
                      TRIALS_PER_HOUR,
                      TOTAL_ML]
        for cn in curveNames:
            self.curves[cn] = LineDotCurve(self.plot, cn)
            self.curves[cn].set_color(get_color(cn))
            self.legend.addItem(self.curves[cn].lineCurve, name=cn)

    def add_point(self, curveName, x, y, data=""):
        self.curves[curveName].add_data(x,y,data)

    def update(self):
        for cn in self.curves:
            self.curves[cn].update()

    def hide_curve(self, curveName):
        self.curves[curveName].hide()

    def update_checked(self):
        """
        Look at UI checkboxes, display appropriate curves.
        Called after UI updates and when date is set.
        """

        #hide all curves
        self.legend.scene().removeItem(self.legend)
        for cn in self.curves:
            self.hide_curve(cn)

        #show just the relevant ones
        self.legend = self.plot.plotItem.addLegend()

        namesToShow = []
        if self.mainUI.chkDiscriminationRatePerf.isChecked():
            namesToShow.append(CORRECT_DISCRIMINATION_RATE)
        if self.mainUI.chkTaskErrorRatePerf.isChecked():
            namesToShow.append(TASK_ERROR_RATE)
        if self.mainUI.chkTotalmLPerf.isChecked():
            namesToShow.append(TOTAL_ML)
        if self.mainUI.chkTrialsPerHourPerf.isChecked():
            namesToShow.append(TRIALS_PER_HOUR)

        for cn in namesToShow:
            self.curves[cn].show()
            self.legend.addItem(self.curves[cn].lineCurve, name=cn)

    def update_session(self):
        """Called when user selects a different session to display."""
        if self.mainUI is not None:
            sessionStr = self.mainUI.cmbSession.getSelected()

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

        dbPerformance = DbPerformance().get(shrewName)
        if len(dbPerformance.keys()) == 0:
            return

        session = self.mainUI.selectedSession
        if session not in dbPerformance:
            #print session, " not in ", shelf.keys()
            return
        sessionData = dbPerformance[session]

        for cn in sessionData.keys():
            if cn in self.curves:
                pointList = sessionData[cn] #each curve entry is an (x, y) tuple already.
                if not isinstance(pointList, list):
                    print shrewName, session, cn, pointList
                    continue
                for (x, y) in pointList:
                    self.curves[cn].add_data(x, y, None)

        self.update_checked()

        for cn in self.curves:
            self.curves[cn].update()



    def clear_curves(self):
        for cn in self.curves:
            self.curves[cn].clear()

def add_test_points(gp):
    n=100
    secondsPerTrial = 30
    for i in range(n):
        t = (i+10)*secondsPerTrial
        gp.add_point(CORRECT_DISCRIMINATION_RATE, t, random.random()*100)
        gp.add_point(TASK_ERROR_RATE, t, random.random()*50)
        gp.add_point(TRIALS_PER_HOUR, t, random.random()*30)
        gp.add_point(TOTAL_ML, t, random.random()*30)
    gp.update()


if __name__ == "__main__":
    # make an application for the sensor graph
    app = QtGui.QApplication(sys.argv)
    mw = QtGui.QMainWindow()

    gp = GraphPerformance(None)
    add_test_points(gp)
    mw.setCentralWidget(gp.plot)

    mw.setGeometry(200, 200, 800, 600)

    mw.show()
    app.exec_()

# GraphUI: graph_ui.py
# Max Planck Florida Institute for Neuroscience
# Last Modified: 16 March 2018

from __future__ import division
from PyQt4 import QtCore, QtGui, uic
import os
import json
import threading
import traceback
import time
import sys
sys.path.append("..")

import pyqtgraph as pg

from ui_graphs.graph_performance import GraphPerformance
from ui_graphs.graph_events import GraphEvents
from ui_graphs.graph_history import GraphHistory
from ui_graphs.graph_lick_times import GraphLickTimes
from ui_graphs.graph_text_data import update_text_data

from devices.available import get_serial_ports, get_cameras
from db import create_db_files
from db.server_data import *
from db.create_db_files import *

# load the .ui files
ShrewDriver_class = uic.loadUiType("ui/graph_ui.ui")[0]


class GraphUI(QtGui.QMainWindow, ShrewDriver_class):

    # #--- Signals to accept ---#
    # self.sig_add_data.connect(self._add_data)
    # self.sig_add_trace.connect(self._add_trace)
    # self.sig_set_threshold.connect(self._set_threshold)

    def __init__(self, parent=None):

        # pyqt setup
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        # current selections
        self.selectedAnimal = None  # type: Shrew
        self.selectedSession = None  # type: str
        self.selectedTask = None  # type: callable
        self.selectedConfig = None  # instance of a config class

        self.displayedAnimal = self.selectedAnimal
        self.displayedSession = self.selectedSession

        # UI sub-objects
        self.performancePlot = None
        self.historyPlot = None
        self.runPlot = None
        self.movieWidget = None

        # Graphs
        self.graphEvents = GraphEvents(self)
        self.graphPerformance = GraphPerformance(self)
        self.graphHistory = GraphHistory(self)
        self.graphLickTimes = GraphLickTimes(self)

        self.tabEventsLayout.addWidget(self.graphEvents.plot)
        self.tabPerformanceLayout.addWidget(self.graphPerformance.plot, 2, 0,
                                            1, 4)
        self.lickPlotFrameLayout.addWidget(self.graphLickTimes.gw)
        self.tabHistoryLayout.addWidget(self.graphHistory.plot, 2, 0, 1, 4)

        # checkbox actions
        self.chkDiscriminationRateHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkSPlusResponseRateHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkSMinusRejectRateHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkTaskErrorRateHist.stateChanged.connect(self.graphHistory.update_checked)

        self.chkTotalmLHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkmLPerHourHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkTrialsHist.stateChanged.connect(self.graphHistory.update_checked)
        self.chkTrainingDurationHist.stateChanged.connect(self.graphHistory.update_checked)

        self.chkDiscriminationRatePerf.stateChanged.connect(self.graphPerformance.update_checked)
        self.chkTaskErrorRatePerf.stateChanged.connect(self.graphPerformance.update_checked)
        self.chkTotalmLPerf.stateChanged.connect(self.graphPerformance.update_checked)
        self.chkTrialsPerHourPerf.stateChanged.connect(self.graphPerformance.update_checked)

        self.rdoHistogram.toggled.connect(self.graphLickTimes.update_checked)
        self.rdoTrialNumber.toggled.connect(self.graphLickTimes.update_checked)

        # combo box actions
        self.cmbAnimal.currentIndexChanged.connect(self.set_animal)
        self.cmbSession.currentIndexChanged.connect(self.set_session)

        # button actions
        self.btnCopyServerData.clicked.connect(self.copy_server_data)
        self.btnProcessLocalData.clicked.connect(self.process_local_data)

        # populate devices, graphs, shrews, etc.
        self.cameras = get_cameras()
        self.serialPorts = get_serial_ports()

        self.animals = []
        for f in os.listdir(DATA_DIR):
            if os.path.isdir(DATA_DIR + os.sep + f):
                self.animals.append(f)

        # results in population of session combo box and updating of graphs
        # as well.
        self.refresh_animals()

        # used by task
        self.stopTask = True
        self.taskThread = None

    def refresh_animals(self):
        """Fill in animals combo box, which in turn updates other stuff."""
        for a in self.animals:
            self.cmbAnimal.addItem(a.capitalize())
        self.set_animal()

    def refresh_sessions(self):
        """Reloads database for selected animal"""
        self.cmbSession.clear()
        try:
            sessions = create_db_files.get_sessions_for_shrew(self.selectedAnimal)
            for s in reversed(sessions):
                self.cmbSession.addItem(s)
            self.cmbSession.setCurrentIndex(0)

        except Exception as e:
            print "Can't load db for animal: ", self.selectedAnimal
            print traceback.print_exc()

    def update_graphs(self):
        """Loads the db entries for this session and updates their graphs on
        the screen."""

        if (self.displayedAnimal == self.selectedAnimal and
                self.displayedSession == self.selectedSession):
            # Selections didn't change
            return

        self.displayedAnimal = self.selectedAnimal
        self.displayedSession = self.selectedSession

        # print("  loading text data...")
        update_text_data(self)
        # print("  loading history graph...")
        self.graphHistory.load_db()
        # print("  loading performance graph...")
        self.graphPerformance.load_db()
        # print("  loading events graph...")
        self.graphEvents.load_db()
        # print("  loading lick times graph...")
        self.graphLickTimes.load_db()
        # print("  Loaded.")

    # --- Combo box callbacks --- #
    def set_animal(self):
        """Lets the user select the animal to view data."""

        for a in self.animals:
            if a.lower() == str(self.cmbAnimal.currentText()).lower():
                self.selectedAnimal = a  # type: Shrew
                self.setWindowTitle(self.selectedAnimal.capitalize() + " - ShrewDriver")
        try:
            self.refresh_sessions()
        except:
            traceback.print_exc()

    def set_config(self):
        """Sets the config for the selected animal."""

        for c in self.selectedAnimal.configs:
            if c.__name__.lower() == str(self.cmbConfig.currentText()).lower():
                # Will be an instance of the class, not the class itself
                self.selectedConfig = c()

    def set_task(self):
        """Selects the task type"""
        for t in self.selectedAnimal.tasks:
            if t.__name__.lower() == str(self.cmbTask.currentText()).lower():
                self.selectedTask = t

    def set_session(self):
        if str(self.cmbSession.currentText()) == "":
            return
        self.selectedSession = str(self.cmbSession.currentText())
        print "session set to " + self.selectedSession
        self.update_graphs()

    # --- Button callbacks --- #
    def copy_server_data(self):
        print(r"Connecting to \\mpfi.org...")
        get_server_data()

    def process_local_data(self):
        update_dbs()
        print "*** Program must restart to load new information. Exiting -- " \
              "please restart to see the updated data! ***"
        sys.exit(0)

    # --- Misc --- #
    def set_combo_box(self, cbx, value):
        index = cbx.findText(str(value))
        cbx.setCurrentIndex(index)

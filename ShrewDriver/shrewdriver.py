#!/usr/bin/env python2.7

# shrewdriver.py: Shrew Driver
# Authors: Theo Walker, Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 02/23/2018

# Description: Automated training system for training tree shrews to
# discriminate visual stimuli. Using it, one experimenter can train many
# animals simultaneously. Run this file to start shrew training. When used for
# behavioral experiments, the user has the option to run an eye-tacking script
# simultaneously with stimulus presentation and data collection.

from __future__ import division

from PyQt4 import QtCore, QtGui, uic
import itertools
import glob
import time
import datetime
import os
import shutil
import fileinput
import operator
import serial
import serial.tools.list_ports
import sys
from subprocess import call
import platform
import cPickle as pkl

# ShrewDriver Packages
from util.enumeration import *
from constants.task_constants import *
from task.training import *

# UI Files
from ui.interact_2AFC import InteractUI_2AFC
from ui.interact import InteractUI

# Calibration and Image Processing Packages
from calibrator import *
from image_processing.ROISelect import *
from image_processing.SubpixelStarburstEyeFeatureFinder import *

# Cameras
from devices.camera_reader import *
try:
    from devices.run_Grasshopper2 import *
except:

    pass

if platform.platform().startswith('Windows'):
    import _winreg as winreg

# load the .ui files
ShrewDriver_class = uic.loadUiType("ui" + os.sep + "shrewdriver_2AFC.ui")[0]

# remove stupid font files that cause matplotlib warning
import matplotlib as mpl

'''
Run this file to start shrew training.
'''


class ShrewDriver(QtGui.QMainWindow, ShrewDriver_class):
    """
    UI logic. Tightly coupled to the Training class, see task/training.py.
    """

    # define signals that we will accept and use to update the UI
    sigTrialEnd = QtCore.pyqtSignal()

    def __init__(self, parent=None):

        # ------------------------------------------------------------
        # EyeTracker Initialization
        # ------------------------------------------------------------

        # Initialize calibrator and feature finder
        self.camera_device = None
        self.calibrator = None
        self.ellipse = None

        self.feature_finder = SubpixelStarburstEyeFeatureFinder()

        # -------------------------------------------------------------
        # Create calibrator object
        # This calibrator object is just a shell. The camera and feature finder are not implemented until the
        # calibration sequence is called so other parameters can be set by drop downs, etc.
        self.calibrator = StahlLikeCalibrator(self.camera_device, self.feature_finder,
                                              d_halfrange=60,
                                              d_guess=483,  # distance from eyeball center to camera sensor [mm]
                                              Dx=1)  # a quantum of stage displacement in millimeters

        # Guess for pupil and CR positions
        self.guess = {"pupil_position": array([0, 0]), "cr_position": array([0, 0])}

        # Edges of ROI in relation to full frame
        self.verticesROI = []
        self.ROI_diff = []

        # ------------------------------------------------------------
        # ShrewDriver and UI Initialization
        # ------------------------------------------------------------

        # make Qt window
        QtGui.QMainWindow.__init__(self, parent)
        self.setupUi(self)

        self.training = None  # becomes a training instance when user hits Start

        # check if a calibration file exists or if we want to skip calibration and eye tracking
        self.isCalibrated = False
        self.useEyetracking = False
        self.setROI = False

        # check if we want to use optogenetics in this experiment
        self.useOpto = False
        # if we only want to use optogenetics on the first stim in a GNG task
        self.useOptoFSOnly = False

        # set class variables
        self.isRecording = False
        self.baseDataPath = "C:\ShrewData" + \
                            os.sep
        self.baseMoviePath = ".." + os.sep + ".." + os.sep + "DT_collab_movies" + os.sep
        self.workingDir = os.getcwd() + os.sep
        self.moviePath = None
        self.dateStr = str(datetime.date.today())
        self.sessionNumber = 1
        self.experimentPath = ""    # set when recording starts
        self.sessionFileName = ""   # likewise

        self.serialPorts = []
        self.animalNames = []
        self.cameraIDs = []
        
        self.animalName = ""
        self.taskType = ""
        self.sensorPortName = ""
        self.leftsyringePortName = ""
        self.rightsyringePortName = ""
        self.stimPortName = ""
        self.airPuffPortName = ""
        self.eyeCameraID = None
        self.observationCameraID = None
        
        self.trialHistory = []

        # dropdown actions
        self.cbAnimalName.currentIndexChanged.connect(self.set_animal)
        self.cbTaskType.currentIndexChanged.connect(self.set_task)
        self.cbSensors.currentIndexChanged.connect(self.set_sensor_port)
        self.cbLeftSyringePump.currentIndexChanged.connect(self.set_leftsyringe_port)
        self.cbRightSyringePump.currentIndexChanged.connect(self.set_rightsyringe_port)
        self.cbVisualStim.currentIndexChanged.connect(self.set_stim_port)
        self.cbAirPuff.currentIndexChanged.connect(self.set_air_puff_port)
        self.cbEyeCameraID.currentIndexChanged.connect(self.set_eye_camera_ID)
        self.cbBehaviorCameraID.currentIndexChanged.connect(self.set_observation_camera_ID)

        # init dropdown choices
        self.get_animal_dirs()
        self.get_available_serial_ports()
        self.get_available_cameras()
        self.get_available_tasks()
        
        # menu actions
        self.actionQuit.triggered.connect(self.quit)
        
        # button actions
        self.btnNewCalibration.clicked.connect(self.confirm_cal)
        self.btnSelectROI.clicked.connect(self.selectROI)
        self.btnStartRecording.clicked.connect(self.start_recording)

        # checkbox actions
        self.chkbOpto.clicked.connect(self.set_opto)
        self.chkbOptoFS.clicked.connect(self.set_opto_fs)

        # signal actions
        self.sigTrialEnd.connect(self.trial_end)

        # populate initial
        self.set_animal()
        
    # -- Init Functions -- #
    def get_animal_dirs(self):
        """ Searches the ShrewData folder and scrapes the animal names."""
        self.animalDirs = glob.glob(self.baseDataPath + '*')
        self.cbAnimalName.addItem("--Select Animal--")
        for animalDir in self.animalDirs:
            if os.path.isdir(animalDir):
                namePos = animalDir.rfind(os.sep)+1
                animalName = animalDir[namePos:]
                self.cbAnimalName.addItem(animalName)
        
    def get_available_serial_ports(self):
        """Searches available serial ports. handles Linux and Windows cases.
        On Windows this searches the Hardware Registry, on Linux it looks for
        /dev/tty ports."""
        try:
            # Uses the Win32 registry to return a iterator of serial
            # (COM) ports existing on this computer.
            serialPath = 'HARDWARE\\DEVICEMAP\\SERIALCOMM'
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, serialPath)
            for i in itertools.count():
                try:
                    val = winreg.EnumValue(key, i)
                    self.serialPorts.append(val[1])
                except EnvironmentError:
                    break
        except:
            # Searches available COM ports a la Unix style
            # this excludes your current terminal "/dev/tty"
            ports = serial.tools.list_ports.comports()
            self.serialPorts = [port[0] for port in ports if port[-1] != 'n/a']

        self.serialPorts = sorted(self.serialPorts)
        
        self.cbVisualStim.addItem("PsychoPy")
        self.cbAirPuff.addItem("None")
        self.cbEyeCameraID.addItem("None")
        self.cbBehaviorCameraID.addItem("None")
        self.cbEyeCameraID.addItem('Point_Grey')

        for serialPort in self.serialPorts:
            self.cbSensors.addItem(serialPort)
            self.cbLeftSyringePump.addItem(serialPort)
            self.cbRightSyringePump.addItem(serialPort)
            self.cbVisualStim.addItem(serialPort)
            self.cbAirPuff.addItem(serialPort)

    def get_available_cameras(self):
        """Searches the Windows Hardware registry for available video devices,
        or the Linux /dev/video ports"""
        try:
            cameraPath = 'HARDWARE\\DEVICEMAP\\VIDEO'
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, cameraPath)
            for i in itertools.count():
                try:
                    val = winreg.EnumValue(key, i)
                    self.cameraIDs.append(val[0])

                    for j, cameraID in enumerate(self.cameraIDs):
                        self.cbBehaviorCameraID.addItem(str(j))
                        self.cbEyeCameraID.addItem(str(j))

                except EnvironmentError:
                    break
        except:
            # Searches available COM ports a la Unix style
            # this excludes your current terminal "/dev/tty"
            ports = serial.tools.list_ports.comports()
            self.cameraIDs = [port[0] for port in ports if port[-1] != 'n/a']
            self.cameraIDs.append(*glob.glob('/dev/video*'))
            for cam in self.cameraIDs:
                if 'S' in cam or 'video' in cam:
                    self.cbBehaviorCameraID.addItem(str(cam[-1]))
                    self.cbEyeCameraID.addItem(str(cam[-1]))

    def get_available_tasks(self):
        """Initiates a GNG task in the Task Type dropdown menu."""
        self.cbTaskType.addItems(["Go-no-Go"])

    # -- Button Actions -- #
    def start_recording(self):
        """Begins recording on Start button press. Saves the port settings for
        the animal. Creates a CPickle file to pass eye tracking parameters to
        the eye tracking subprocess if necessary. A second button press stops
        training."""
        if not self.isRecording:
            self.isRecording = True
            self.btnStartRecording.setText("Stop Recording")
            
            self.save_animal_settings()
            
            # start a new recording session by making a dir to put the data in
            self.make_session()

            # Pickle data dictionary to pass to subprocess
            data = self.guess.copy()
            data['ellipse'] = self.ellipse
            data['cameraID'] = self.eyeCameraID
            data['ROI'] = self.verticesROI
            data['animalID'] = self.animalName
            data['basepath'] = self.baseDataPath
            data['session_path'] = self.experimentPath + self.sessionFileName
            pkl_file = open('data.pkl', 'wb')
            pkl.dump(data, pkl_file)
            pkl_file.close()

            # start camera recording, live visualization, and training program
            self.start_training()
            
        else:
            self.training.stop()
            self.isRecording = False
            self.btnStartRecording.setEnabled(False)
            # self.btnStartRecording.setText("Start Recording")
    
    def save_animal_settings(self):
        """Saves last used serial port assignments."""
        self.devicesPath = self.baseDataPath + self.animalName + os.sep + "devices.txt"
        self.devicesFile = open(self.devicesPath, 'w')
        if self.taskType.startswith('2'):
            self.devicesFile.write('arduino ' + self.sensorPortName + "\n")
            self.devicesFile.write('leftsyringe ' + self.leftsyringePortName + "\n")
            self.devicesFile.write('rightsyringe ' + self.rightsyringePortName + "\n")
            self.devicesFile.write('stim ' + self.stimPortName + "\n")
            self.devicesFile.write('eye_camera ' + str(self.eyeCameraID) + "\n")
            self.devicesFile.write('behave_camera ' + str(self.observationCameraID) + "\n")
            self.devicesFile.write('airpuff ' + str(self.airPuffPortName) + "\n")
            self.devicesFile.close()
        else:
            self.devicesFile.write('arduino ' + self.sensorPortName + "\n")
            self.devicesFile.write('syringe ' + self.leftsyringePortName + "\n")
            self.devicesFile.write('stim ' + self.stimPortName + "\n")
            self.devicesFile.write('eye_camera ' + str(self.eyeCameraID) + "\n")
            self.devicesFile.write('behave_camera ' + str(self.observationCameraID) + "\n")
            self.devicesFile.write('airpuff ' + str(self.airPuffPortName) + "\n")
            self.devicesFile.close()
        
    def load_animal_settings(self):
        """Parses 'devices.txt' for last used serial port assignments."""
        self.devicesPath = self.baseDataPath + self.animalName + os.sep + "devices.txt"
        self.moviePath = self.baseMoviePath + self.animalName + "_movie" + os.sep
        fileinput.close()              # ensure no file input is active already
        print 'Loading settings from ' + self.devicesPath
        if os.path.isfile(self.devicesPath):
            for line in fileinput.input(self.devicesPath):
                line = line.rstrip()
                toks = line.split(' ')

                if toks[0].lower() == 'arduino':
                    self.sensorPortName = toks[1]
                    self.set_combo_box(self.cbSensors, toks[1])
                if toks[0].lower() == 'stim':
                    self.stimPortName = toks[1]
                    self.set_combo_box(self.cbVisualStim, toks[1])
                if toks[0].lower() == 'eye_camera':
                    self.eyeCameraID = toks[1]
                    self.set_combo_box(self.cbEyeCameraID, toks[1])
                if toks[0].lower() == 'behave_camera':
                    self.observationCameraID = toks[1]
                    self.set_combo_box(self.cbBehaviorCameraID, toks[1])
                if toks[0].lower() == 'airpuff':
                    if toks[1] == "None":
                        self.airPuffPortName = None
                    else:
                        self.airPuffPortName = toks[1]
                    self.set_combo_box(self.cbAirPuff, toks[1])

                # check to see if this is a 2port enabled animal
                # if there's 2 ports, we have generic:1 port, 2 port,
                # 2 port-alt and animal:go-no-go, 2AFC tasks
                if toks[0] == 'leftsyringe':
                    print '2 ports available'

                    if self.animalName == 'Generic':
                        self.cbTaskType.clear()
                        self.cbTaskType.addItems(["1 port", "2 port",
                                                  "2 port alt"])
                    else:
                        self.cbTaskType.clear()
                        self.cbTaskType.addItems(["Go-no-Go", "Go-no-Go Early", "2AFC",
                                                  "2AFC_OE"])

                    if toks[0].lower() == 'leftsyringe':
                        self.leftsyringePortName = toks[1]
                        self.set_combo_box(self.cbLeftSyringePump, toks[1])
                    if toks[0].lower() == 'rightsyringe':
                        self.rightsyringePortName = toks[1]
                        self.set_combo_box(self.cbRightSyringePump, toks[1])

                # if there's only 1 port, we only have generic:1 port option and animal: go-no-go
                elif toks[0] == 'syringe':
                    print '2 ports not available'

                    if self.animalName == 'Generic':
                        self.cbTaskType.clear()
                        self.cbTaskType.addItems(["1 port"])
                    else:
                        self.cbTaskType.clear()
                        self.cbTaskType.addItems(["Go-no-Go", "Go-no-Go Early"])

                    if toks[0].lower() == 'syringe':
                        # self.leftsyringePortName = toks[1]
                        self.set_combo_box(self.cbLeftSyringePump, toks[1])

    def load_calibration_file(self):
        """Load calibration file for eye tracking if it exists."""
        self.calibratorFile = self.animalName + "_calibrator"
        self.calibratorPath = self.baseDataPath + self.animalName + "/calibrator/"
        fileinput.close()

        if os.path.isfile(self.calibratorPath + self.calibratorFile):
            self.isCalibrated = True
            self.calibrator.load_parameters(self.calibratorPath + self.calibratorFile)
        else:
            self.isCalibrated = False
            if self.animalName != "--Select Animal--":
                print "No calibration file found!"

            if (self.animalName != "--Select Animal--") and not os.path.isdir(self.calibratorPath):
                os.makedirs(self.calibratorPath)

    # Then I need a big conditional that pulls up different set of files based on task-type
    # 1) deactivate right-syringe box if we're doing a go-no-go task
    # 2) I can pass tasktype arguments into start_training and start_interact_UI below
    def load_task_settings(self):
        """Disables/enabales right syringe pumps if not using/using GNG task."""
        if self.taskType.startswith('2'):
            self.enable_combo_box(self.cbRightSyringePump)
        else:
            self.disable_combo_box(self.cbRightSyringePump)

    def set_combo_box(self, cbx, value):
        """
        Args:
            cbx: Combo box you want to manipulate
            value: Updated combo box value

        Returns: Generalized function to set combo box
        """
        # print "found value " + str(value) + " at index " + str(index)
        index = cbx.findText(str(value))
        cbx.setCurrentIndex(index)

    def disable_combo_box(self, cbx):
        """
        Args:
            cbx: Combo box you want to manipulate

        Returns: Generalized function to disable combo box

        """
        cbx.setEnabled(False)

    def enable_combo_box(self, cbx):
        cbx.setEnabled(True)

    def make_session(self):
        """Creates a new directory for each recording session"""
        # make the dirs for a new recording session
        animalPath = self.baseDataPath + self.animalName + os.sep
        datePath = animalPath + self.dateStr + os.sep
        if not os.path.exists(datePath):
            os.makedirs(datePath)
        for i in range(1, 10000):
            sessionPath = datePath + str(i).zfill(4) + os.sep
            if not os.path.exists(sessionPath):
                self.sessionNumber = i
                os.makedirs(sessionPath)
                self.experimentPath = sessionPath
                break
        
        self.sessionFileName = self.animalName + '_' + self.dateStr + '_' + str(self.sessionNumber)

    # -- Signal Handlers -- #
    def trial_end(self):
        """Signals end of a trial"""
        self.update_results()

    def update_results(self):
        """Gets results from analyzer and writes them as plain text to the
        summary file."""
        message = self.training.analyzer.get_results_str()

        if message is not None:
            self.txtTrialStats.setPlainText(message)

            summaryFile = self.training.analyzer.get_summary_path()
            with open(summaryFile, 'w') as fh:
                fh.write(message)
    
    # -- Dropdown Actions -- #
    def set_animal(self):
        """Loads last used animal settings and calibration file, if available."""
        self.animalName = str(self.cbAnimalName.currentText())
        self.load_animal_settings()
        self.load_calibration_file()

    # choose from either go/no-go or 2AFC0-x
    def set_task(self):
        """Set task-specific parameters"""
        self.taskType = str(self.cbTaskType.currentText())
        self.setWindowTitle(self.animalName + "-" + self.taskType)
        self.load_task_settings()

    def set_sensor_port(self):
        self.sensorPortName = str(self.cbSensors.currentText())

    def set_leftsyringe_port(self):
        self.leftsyringePortName = str(self.cbLeftSyringePump.currentText())

    def set_rightsyringe_port(self):
        self.rightsyringePortName = str(self.cbRightSyringePump.currentText())

    def set_stim_port(self):
        self.stimPortName = str(self.cbVisualStim.currentText())

    def set_eye_camera_ID(self):
        self.eyeCameraID = str(self.cbEyeCameraID.currentText())

    def set_observation_camera_ID(self):
        self.observationCameraID = str(self.cbBehaviorCameraID.currentText())

    def set_air_puff_port(self):
        self.airPuffPortName = str(self.cbAirPuff.currentText())

    def set_opto(self):
        if self.chkbOpto.isChecked:
            self.useOpto = True
            self.enable_combo_box(self.chkbOptoFS)
        else:
            self.useOpto = False
            self.disable_combo_box(self.chkbOptoFS)

    def set_opto_fs(self):
        if self.chkbOptoFS.isChecked:
            self.useOptoFSOnly = True
        else:
            self.useOptoFSOnly = False

    # -- Menu Actions -- #
    def quit(self):
        """Stops training by calling the training class stop method"""
        if self.training is not None:
            self.training.stop()
            time.sleep(0.5)             # wait for everything to wrap up nicely
        self.close()

    def closeEvent(self, event):
        # Overrides the PyQt function of the same name, so don't rename this.
        # Happens when user clicks "X".
        self.quit()
        event.accept()

    # -- ROI Sequence -- #
    def selectROI(self):
        """Creates an ROI selection sequence. Returns vertices of ROI rectangle
        and seed point for feature finder. Sets the ROI in Feature Finder and
        creates the calibrator camera instance.
        """
        if self.eyeCameraID == "None":
            print "An eye tracking camera must be installed. Select an eye tracking camera."

        else:
            get_roi = ROISelect(self.eyeCameraID)
            get_roi.findROI()
            self.verticesROI, self.ROI_diff, pupil, cr, self.ellipse = get_roi.getData()

            if pupil != []:
                self.guess["pupil_position"] = [pupil[0][0], pupil[0][1]]

            if cr != []:
                self.guess["cr_position"] = [cr[0][0], cr[0][1]]

            self.setROI = True
            del get_roi

    # -- Calibrator Sequence --#
    def confirm_cal(self):
        """Ask user to confirm using last-used calibrator or to run a new calibration"""
        # Check if there is a calibration file that you would like to overwrite
        if self.isCalibrated:
            self.overwrite_dialogue()
        else:
            self.run_calibrator()

    def overwrite_dialogue(self):
        """Ask if user wants to overwrite calibration file. Calls a popup window for confirmation."""
        # Create a popup dialogue to confirm the user wants to overwrite existing calibration file
        flags = QtGui.QMessageBox.Yes
        flags |= QtGui.QMessageBox.No
        msg = "Overwrite existing calibration file?"
        response = QtGui.QMessageBox.warning(self, self.animalName + " - Overwrite Calibration", msg, flags)

        # If YES is pressed
        # There may be a better way to do this, but I don't know how
        if response == 16384:
            self.run_calibrator()

    def skip_cal_dialogue(self):
        """Ask if user wants to run program without calibration. This forces the program to skip
         the calibration sequence and not initiate eye tracking.
         """

        if not self.isCalibrated and not self.isRecording and self.setROI:
            # Create a popup dialogue to confirm the user wants to skip
            # calibration and not use eyetracking
            flags = QtGui.QMessageBox.Yes
            flags |= QtGui.QMessageBox.No
            msg = "Are you sure you want to skip calibration?"
            response = QtGui.QMessageBox.warning(self, self.animalName + " - Skip Calibration", msg, flags)

            # If YES is pressed
            # There may be a better way to do this, but I don't know how
            if response == 16384:
                self.start_recording()

        elif self.isCalibrated and not self.isRecording and not self.setROI:
            # Force user to choose ROI before starting recording if already calibrated
            msgBoxROI = QtGui.QMessageBox()
            msgBoxROI.setText("A ROI must be selected before proceeding.")
            msgBoxROI.exec_()

            self.selectROI()
            self.start_recording()

        else:
            # If the animal already has a calibration file
            self.start_recording()

    def run_calibrator(self):
        print "Beginning calibration sequence."
        self.calibrate = RunCalibrator(self)
        self.calibrate.begin()
        self.isCalibrated = True

    # -- Other -- #
    def start_training(self):
        """Starts training. Called by start_recording on button click."""
        self.training = Training(self)
        self.training.start()

    def show_interact_ui(self, task):
        """If allowed, this will be shown when the user starts recording.
        Called by training.py."""
        if self.taskType.startswith('2'):
            self.interactUI = InteractUI_2AFC()
        else:
            self.interactUI = InteractUI()

        self.interactUI.set_task(task)


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myWindow = ShrewDriver(None)
    myWindow.show()
    app.exec_()

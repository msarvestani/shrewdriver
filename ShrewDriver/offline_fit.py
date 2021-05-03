#!/usr/bin/env python

# offline_fit.py: offline eye tracking
# Max Planck Florida Institute for Neuroscience (MPFI)
# Author: Matthew McCann (@mkm4884)
# Created: 01/09/2017
# Last Modifided: 02/16/2017

# Description: Simple GUI that extends the fit preview functionality for the
# duration of a prerecorded movie, allowing the user to dynamically update
# their fitting parameters and image adjustments. Saves a video and eye
# tracking data.

from __future__ import division

# General packages
from PyQt4 import QtCore, QtGui, uic
import _winreg as winreg
import itertools
import time
import datetime
import os
import glob
import shutil
import fileinput
import operator
import subprocess
import cPickle as pkl
from Queue import Queue
import sys

# Video Reader
from devices.video_file_reader import *

# feature finder, ROI, and calibrator
from image_processing.SubpixelStarburstEyeFeatureFinder import *
from image_processing.ROISelect import *
from calibrator.StahlLikeCalibrator import *

# load the UI files
OfflineTracking_class = uic.loadUiType("ui/offline_fit.ui")[0]


class OfflineFit(QtGui.QMainWindow, OfflineTracking_class):

    def __init__(self, parent=None):
        # ------------------------------------------------------------
        # UI Initialization
        # ------------------------------------------------------------
        # make Qt window
        super(OfflineFit, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Offline Eye Tracking')

        # becomes a fitting instance when user hits Start
        self.fitting = None
        self.isFitting = False

        # set class variables
        self.baseDataPath = '../../../Data/'  # change this for local machine
        self.calFile = ''
        self.dataDir = ''
        self.vidFile = ''
        self.vidPathFull = ''
        self.animalName = ''
        self.animalDirs = ''

        # dropdown actions
        self.cbAnimal.currentIndexChanged.connect(self.set_animal)

        # button actions
        self.btnChooseVid.clicked.connect(self.set_vid)
        self.btnSelectROI.clicked.connect(self.selectROI)
        self.btnStart.clicked.connect(self.start)

        # init dropdown choices
        self.get_animal_dirs()

        # ------------------------------------------------------------
        # Eye Tracking Initialization
        # ------------------------------------------------------------

        # class variables
        self.calibratorFile = ''
        self.calibratorPath = ''
        self.temp_image_settings_path = ''
        self.cameraID = 'recorded'

        # check if a calibration file exists or if we want to skip calibration and eye tracking
        self.isCalibrated = False
        self.onlyEyeMovements = False
        self.fullGazeTracking = False
        self.setROI = False

        # Initialize calibrator and feature finder
        self.camera_device = None
        self.calibrator = None
        self.imaging_modality = '2P'
        self.feature_finder = SubpixelStarburstEyeFeatureFinder(modality=self.imaging_modality)

        # -------------------------------------------------------------
        # Create calibrator object
        # This calibrator object is just a shell. The camera and feature finder
        # are not implemented until the calibration sequence is called so other
        # parameters can be set by drop downs, etc.
        self.calibrator = StahlLikeCalibrator(self.camera_device, self.feature_finder,
                                              d_halfrange=60,
                                              d_guess=483,  # distance from eyeball center to camera sensor [mm] (~19 inches)
                                              Dx=1)  # a quantum of stage displacement in millimeters

        # Guess for pupil and CR positions
        self.guess = {"pupil_position": [0, 0], "cr_position": [0, 0]}

        # Edges of ROI in relation to full frame
        self.verticesROI = []
        self.ROI_diff = []

    # -- Init Functions _-- #
    def get_animal_dirs(self):
        """Scrape animal folder names from the base data directory and display
        them in the dropdown"""
        self.cbAnimal.addItem("--Select Animal--")
        self.animalDirs = glob.glob(self.baseDataPath + '*')
        for animalDir in self.animalDirs:
            if os.path.isdir(animalDir):
                namePos = animalDir.rfind("\\")+1
                animalName = animalDir[namePos:]
                self.cbAnimal.addItem(animalName)

    # -- Dropdown Actions -- #
    def set_animal(self):
        """Set selected animal, enable the choose video button, set relative paths"""
        self.animalName = str(self.cbAnimal.currentText())
        if self.animalName != '--Select Animal--':
            self.txtUpdates.append(self.animalName + ' selected!')
            self.btnChooseVid.setEnabled(True)
            self.dataDir = self.baseDataPath + os.sep + self.animalName + os.sep

    # -- Button Actions -- #
    def set_vid(self):
        """Open file dialogue box so user can select video, enable Select ROI button"""
        self.fileDialog = QtGui.QFileDialog(self, 'Video Files', self.dataDir, 'AVI files (*.avi)')
        self.vidPathFull = self.fileDialog.getOpenFileName()
        self.vidPathFull = str(self.vidPathFull)
        self.vidFile = self.vidPathFull.rsplit(os.sep)[-1]
        self.txtUpdates.setPlainText('Loaded ' + str(self.vidFile))
        if self.vidFile != '':
            self.btnSelectROI.setEnabled(True)

    # -- ROI Sequence -- #
    def selectROI(self):
        """Creates an ROI selection sequence. Returns vertices of ROI rectangle
        and seed point for feature finder. Sets the ROI in Feature Finder and
        creates the calibrator camera instance.
        """

        get_roi = ROISelect('video', vidPath=self.vidPathFull)
        get_roi.findROI()
        self.verticesROI, self.ROI_diff, pupil, cr, self.ellipse = get_roi.getData()

        if pupil != []:
            self.guess["pupil_position"] = [pupil[0][0], pupil[0][1]]

        if cr != []:
            self.guess["cr_position"] = [cr[0][0], cr[0][1]]

        self.setROI = True
        del get_roi
        self.txtUpdates.append('ROI selected')
        self.btnStart.setEnabled(True)

    # -- Menu Actions -- #
    def quit(self):
        if self.fitting is not None:
            self.fitting.communicate()[0]
            time.sleep(0.5)  # wait for everything to wrap up nicely
        if os.path.exists('data.pkl'):
            os.remove('data.pkl')
        self.close()

    def closeEvent(self, event):
        # Overrides the PyQt function of the same name, so you can't rename this.
        # Happens when user clicks "X".
        self.quit()
        event.accept()

    # -- Start Sequence -- #
    def start(self):
        """Saves eye tracking parameters to a .pkl file to get passed to the
        feature finder; starts eye tracking subprocess."""
        if not self.isFitting:
            self.isFitting = True
            self.btnStart.setText('Stop')

            # Pickle data dictionary to pass to subprocess
            data = self.guess.copy()
            data['ellipse'] = self.ellipse
            data['cameraID'] = self.cameraID
            data['ROI'] = self.verticesROI
            data['ROI_diff'] = self.ROI_diff
            data['animalID'] = self.animalName
            data['basepath'] = self.vidPathFull
            pkl_file = open('data.pkl', 'wb')
            pkl.dump(data, pkl_file)
            pkl_file.close()

            # Start Preview GUI
            print 'Starting analysis'
            sys.stdout.flush()
            self.fitting = subprocess.Popen(['python', 'ui/preview_fit.py', '--called'], cwd=os.getcwd())

        else:
            self.btnStart.setEnabled(False)
            self.isFitting = False
            self.fitting.communicate()[0]


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myWindow = OfflineFit(None)
    myWindow.show()
    app.exec_()  # do not change to sys.exit(app.exec_()). This will quit the program without shutting things down nicely or saving the data!!!!

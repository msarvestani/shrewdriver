#!/usr/bin/env python

# preview_fit.py: Preview Starburst Fit User Interface
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Created: 12/14/2016
# Last Modified:

# Description: A GUI to preview pupil tracking fit before beginning a training
# session. Interacts closely with the ShrewDriver script. The user can accuracy
# of the feature finder by adjusting the gamma, contrast, and brightness of the
# raw images, and the search parameters of the starburst feature finder. A live
# preview is displayed. When results are satisfactory, the output is saved to a
#  text file to be loaded by ShrewDriver.

from __future__ import division
import os
from numpy import array
from PyQt4 import QtCore, QtGui, uic
import cPickle as pkl
import sys
import fileinput
import time
import shutil
from Queue import Queue

# This section reads the standard input looking for a flag to specify the
# location of the ui directory
if sys.argv[-1] == '--called':
    # load the .ui files
    print os.getcwd()
    sys.path.append(os.getcwd())
    sys.path.append('..')
    Preview_class = uic.loadUiType("ui/preview_fit.ui")[0]
else:
    # load the .ui files
    sys.path.append('..')
    Preview_class = uic.loadUiType("preview_fit.ui")[0]

# Cameras
from devices.camera_reader import *
from devices.run_Grasshopper2 import *
from devices.video_file_reader import *

# eye tracking stuff
from image_processing.ROISelect import *
from image_processing import SubpixelStarburstEyeFeatureFinder
from eyetracking.pupil_locator import *
from calibrator.StahlLikeCalibrator import *


class PreviewFitUI(QtGui.QMainWindow, Preview_class):

    def __init__(self, parent=None):

        # ------------------------------------------------------------
        # Data Management
        # ------------------------------------------------------------

        # -- IF WE CALL THE SUBPROCESS FROM ANOTHER PROCESS -- #
        if sys.argv[-1] == '--called':
            self.wasCalled = True
            # Unpickle guess dictionary for initial guess, cameraID, and ROI if
            # it exists. This file will only be present if this file was called
            # as a subprocess
            pkl_file = open('data.pkl', 'rb')
            self.guess = pkl.load(pkl_file)
            # This will be a path to a video file for offline analysis and to
            # the main data directory for online
            self.base_path = self.guess['basepath']
            self.animalName = self.guess['animalID']
            self.cameraID = self.guess['cameraID']
            self.ROI = self.guess['ROI']
            ellipse = self.guess['ellipse']

            if 'ROI_diff' in self.guess:
                self.ROI_diff = self.guess['ROI_diff']
                del self.guess['ROI_diff']
            else:
                self.ROI_diff = [0, 0]

            # These variables are present when calling from shrewdriver. From
            # here we can define the current session number and write videos and
            # text data here. If this variable does not exist, is assigned a
            # None value.
            self.sessionFile = self.guess.get('session_path', None)
            if self.sessionFile is not None and self.cameraID != 'recorded':
                self.vidPath = self.sessionFile + '.avi'
                del self.guess['session_path']
            elif self.sessionFile is None and self.cameraID == 'recorded':
                self.vidPath = self.base_path

            del self.guess['basepath'], self.guess['animalID'], \
                self.guess['cameraID'], self.guess['ROI']

            self.guess_i = self.guess.copy()

        # -- IF WE ARE CALLING THE FUNCTION AS A STANDALONE ENTITY -- #
        else:
            # If running as standalone (testing for now)
            self.wasCalled = False
            # Change this based on local machine if running in standalone format
            self.base_path = os.getcwd()
            self.animalName = 'Test'
            self.cameraID = '0'           # Change this based on hardware setup
            get_roi = ROISelect.ROISelect(self.cameraID)
            get_roi.findROI()
            self.ROI, self.roi_diff, pupil, cref, ellipse = get_roi.getData()
            self.guess = {'pupil_position': array(pupil[0]),
                          'cr_position': array(cref[0])}
            self.guess_i = self.guess.copy()
            self.save_vid = False
            self.save_log = False

        # Depending on if we are doing offline or online analysis,
        # the data folder changes
        if self.cameraID != 'recorded':
            self.online = True
            # change this for local machine
            self.base_path = self.base_path + os.sep + self.animalName + os.sep
            self.temp_data_path = self.base_path + os.sep + 'temp_image_settings'
            self.calibratorPath = self.base_path
            # make the folder if it doesn't exist
            if not os.path.exists(self.temp_data_path):
                os.makedirs(self.temp_data_path)
        else:
            self.online = False
            self.base_path = self.base_path.rsplit(os.sep, 1)[0]
            self.calibratorPath = self.base_path.rsplit(os.sep, 2)[0]
            self.temp_data_path = self.base_path

        # assign file name
        self.temp_image_file = self.temp_data_path + os.sep + 'temp_image_settings_file.txt'

        # ------------------------------------------------------------
        # EyeTracker Initialization
        # ------------------------------------------------------------

        # Import Camera, ROI, and fitting settings if available
        self.CameraReader = None

        # Load data to set up parameters for feature finder if available
        self.load_ff_settings()

        # Create buffers to deal with images
        self.frame_queue = Queue()
        self.output_queue = Queue()

        # Set up feature finder pipeline
        self.starburst_ff = \
            SubpixelStarburstEyeFeatureFinder.SubpixelStarburstEyeFeatureFinder(
                modality='2P', pupil_n_rays=self.pupil_n_rays,
                pupil_ray_length=self.pupil_ray_length,
                pupil_threshold=self.pupil_threshold, cr_n_rays=self.cr_n_rays,
                cr_ray_length=self.cr_ray_length, cr_threshold=self.cr_threshold)

        self.ff_pipe = PupilLocator(self.frame_queue, self.starburst_ff,
                                    self.guess, self.vidPath, ROI=self.ROI,
                                    ROI_diff=self.ROI_diff, save_vid=False,
                                    save_log=True, online=self.online,
                                    ellipse=ellipse)

        # load calibrator data
        self.calibratorFile = ''
        self.calibrator = StahlLikeCalibrator(None, self.starburst_ff)
        self.load_calibration_file()

        # Set up booleans
        self.running = False

        # ------------------------------------------------------------
        # UI Setup
        # ------------------------------------------------------------

        # make Qt window
        super(PreviewFitUI, self).__init__(parent)
        self.setupUi(self)
        self.setWindowTitle('Fit Parameter Adjustment')

        # button actions
        self.btnStart.clicked.connect(self.start)
        self.btnResetPar.clicked.connect(self.reset_params)
        self.btnResetGuess.clicked.connect(self.reset_guess)
        self.btnRawVid.clicked.connect(self.show_raw)
        self.btnRawFit.clicked.connect(self.show_raw_fit)
        self.btnAdjFit.clicked.connect(self.show_adj_fit)
        self.btnSobFit.clicked.connect(self.show_sobel_fit)
        self.btnSobFit.setEnabled(False)

        # slider setups
        self.slGamma.setMinimum(1)
        self.slGamma.setMaximum(5)
        self.slGamma.setTickPosition(QtGui.QSlider.TicksBelow)
        self.slGamma.setTickInterval(1)
        self.slGamma.setValue(self.gamma)

        self.slContrast.setMinimum(1)
        self.slContrast.setMaximum(6)
        self.slContrast.setTickPosition(QtGui.QSlider.TicksBelow)
        self.slContrast.setTickInterval(1)
        self.slContrast.setValue(self.contrast)

        self.slBrightness.setMinimum(-75)
        self.slBrightness.setMaximum(75)
        self.slBrightness.setTickPosition(QtGui.QSlider.TicksBelow)
        self.slBrightness.setTickInterval(5)
        self.slBrightness.setValue(self.brightness)

        # spin box setup
        self.spnGamma.setRange(1, 5)
        self.spnGamma.setValue(self.gamma)
        self.spnContrast.setRange(1, 6)
        self.spnContrast.setValue(self.contrast)
        self.spnBrightness.setRange(-75, 75)
        self.spnBrightness.setValue(self.brightness)

        self.spnSobelFrame.setRange(1, 10)
        self.spnSobelFrame.setValue(self.num_frames_sobel)
        self.spnPupilRays.setRange(10, 40)
        self.spnPupilRays.setValue(self.pupil_n_rays)
        self.spnPupilRayLength.setRange(15, 60)
        self.spnPupilRayLength.setValue(self.pupil_ray_length)
        self.spnPupilThresh.setRange(0, 255)
        self.spnPupilThresh.setValue(self.pupil_threshold)
        self.spnCRRays.setRange(5, 10)
        self.spnCRRays.setValue(self.cr_n_rays)
        self.spnCRRayLength.setRange(2, 20)
        self.spnCRRayLength.setValue(self.cr_ray_length)
        self.spnCRThresh.setRange(0, 255)
        self.spnCRThresh.setValue(self.cr_threshold)

        # slider actions (with spin box change)
        self.slGamma.valueChanged.connect(
            lambda: self.change_slider_spin(self.slGamma, self.spnGamma,
                                            self.gamma, 'gamma'))
        self.slContrast.valueChanged.connect(
            lambda: self.change_slider_spin(self.slContrast, self.spnContrast,
                                            self.contrast, 'contrast'))
        self.slBrightness.valueChanged.connect(
            lambda: self.change_slider_spin(self.slBrightness, self.spnBrightness,
                                            self.brightness, 'brightness'))

        # spin box actions (with slider change)
        self.spnGamma.valueChanged.connect(
            lambda: self.change_spin_slider(self.spnGamma, self.slGamma,
                                            self.gamma, 'gamma'))
        self.spnContrast.valueChanged.connect(
            lambda: self.change_spin_slider(self.spnContrast, self.slContrast,
                                            self.contrast, 'contrast'))
        self.spnBrightness.valueChanged.connect(
            lambda: self.change_spin_slider(self.spnBrightness, self.slBrightness,
                                            self.brightness, 'brightness'))

        # spin box actions (no slider change)
        self.spnSobelFrame.valueChanged.connect(
            lambda: self.change_spin(self.spnSobelFrame, self.num_frames_sobel,
                                     'num_frames'))
        self.spnPupilRays.valueChanged.connect(
            lambda: self.change_spin(self.spnPupilRays, self.pupil_n_rays,
                                     'pupil_n_rays'))
        self.spnPupilRayLength.valueChanged.connect(
            lambda: self.change_spin(self.spnPupilRayLength, self.pupil_ray_length,
                                     'pupil_ray_length'))
        self.spnPupilThresh.valueChanged.connect(
            lambda: self.change_spin(self.spnPupilThresh, self.pupil_threshold,
                                     'pupil_threshold'))
        self.spnCRRays.valueChanged.connect(
            lambda: self.change_spin(self.spnCRRays, self.cr_n_rays, 'cr_n_rays'))
        self.spnCRRayLength.valueChanged.connect(
            lambda: self.change_spin(self.spnCRRayLength, self.cr_ray_length,
                                     'cr_ray_length'))
        self.spnCRThresh.valueChanged.connect(
            lambda: self.change_spin(self.spnCRThresh, self.cr_threshold,
                                     'cr_threshold'))

        # show UI
        self.show()

        # start if called
        if self.wasCalled:
            self.start()

    # -- Init Functions -- #
    def load_ff_settings(self):
        """Loads previously used feature finder settings if available."""

        if os.path.isfile(self.temp_image_file):

            print "Loading feature finder parameters from " + str(self.temp_image_file)

            for line in fileinput.input(self.temp_image_file):
                line = line.rstrip()
                toks = line.split(' ')

                if toks[0].lower() == 'sobel_n_frames':
                    self.num_frames_sobel = int(toks[1])
                if toks[0].lower() == 'pupil_n_rays':
                    self.pupil_n_rays = int(toks[1])
                if toks[0].lower() == 'pupil_ray_length':
                    self.pupil_ray_length = int(toks[1])
                if toks[0].lower() == 'pupil_threshold':
                    self.pupil_threshold = int(toks[1])
                if toks[0].lower() == 'cr_n_rays':
                    self.cr_n_rays = int(toks[1])
                if toks[0].lower() == 'cr_ray_length':
                    self.cr_ray_length = int(toks[1])
                if toks[0].lower() == 'cr_threshold':
                    self.cr_threshold = int(toks[1])
                if toks[0].lower() == 'brightness':
                    self.brightness = int(toks[1])
                if toks[0].lower() == 'contrast':
                    self.contrast = int(toks[1])
                if toks[0].lower() == 'gamma':
                    self.gamma = int(toks[1])
        else:
            # Brightness, Contrast, Gamma Correction
            self.contrast = 3
            self.brightness = 0
            self.gamma = 4

            # Starburst parameters
            self.pupil_n_rays = 25
            self.pupil_ray_length = 45
            self.pupil_threshold = 30
            self.cr_n_rays = 10
            self.cr_ray_length = 10
            self.cr_threshold = 60

            # Number of sobel_filtered frames to average
            self.num_frames_sobel = 3

        # Create Duplicates for Parameter Reset
        self.contrast_0 = self.contrast
        self.brightness_0 = self.brightness
        self.gamma_0 = self.gamma
        self.pupil_n_rays_0 = self.pupil_n_rays
        self.pupil_ray_length_0 = self.pupil_ray_length
        self.pupil_threshold_0 = self.pupil_threshold
        self.cr_n_rays_0 = self.cr_n_rays
        self.cr_ray_length_0 = self.cr_ray_length
        self.cr_threshold_0 = self.cr_threshold
        self.num_frames_sobel_0 = self.num_frames_sobel

    def load_calibration_file(self):
        """Loads calibration file if available."""

        self.calibratorPath = self.calibratorPath + os.sep + "calibrator" + os.sep
        self.calibratorFile = self.animalName + "_calibrator"
        fileinput.close()

        if os.path.isfile(self.calibratorPath + self.calibratorFile):
            self.isCalibrated = True
            self.calibrator.load_parameters(self.calibratorPath + self.calibratorFile)
            print 'Calibration file loaded!'
        else:
            self.isCalibrated = False
            print "No calibration file found!"

    # -- slider functions -- #
    def change_slider_spin(self, slide, spin, var, key):
        """
        Generic function to update slider and spin box of the same variable,
        and set the variable in both this class and the feature finder class.

        Args:
            slide: [qt object] slider to be changed
            spin: [qt object] spin box to be changed
            var: the variable to be adjusted
            key: [string] string of the name of the variable

        Returns: changes relevant class variables and sets the corresponding
        variable in the feature finder object
        """

        var = slide.value()
        spin.setValue(var)
        setattr(self, key, var)
        setattr(self.ff_pipe, key, var)
        if key == 'gamma':
            self.ff_pipe.update_parameters()
        # print getattr(self.ff_pipe, key)   # for debugging

    # -- spin box actions -- #
    def change_spin_slider(self, spin, slide, var, key):
        """
        Generic function to update slider and spin box of the same variable,
        and set the variable in both this class and the feature finder class.
        Does the same thing as self.change_slider_spin(), but if the spin box
        is manipulated first.

        Args:
            slide: [qt object] slider to be changed
            spin: [qt object] spin box to be changed
            var: the variable to be adjusted
            key: [string] string of the name of the variable

        Returns: changes relevant class variables and sets the corresponding
        variable in the feature finder object
        """

        var = spin.value()
        slide.setValue(var)
        setattr(self, key, var)
        setattr(self.ff_pipe, key, var)
        if key == 'gamma':
            self.ff_pipe.update_parameters()
        # print getattr(self.ff_pipe, key)  # for debugging

    def change_spin(self, spin, var, key):
        """
        Generic function to update spin boxes and set the variable in both this
        class and the feature finder class.

        Args:
            spin: [qt object] spin box to be changed
            var: the variable to be adjusted
            key: [string] string of the name of the variable

        Returns: changes relevant class variables and sets the corresponding
        variable in the feature finder object
        """

        var = spin.value()
        setattr(self, key, var)
        if key == 'num_frames':
            setattr(self.ff_pipe, key, var)
            # print getattr(self.ff_pipe, key)  # for debugging
        else:
            setattr(self.ff_pipe.ff, key, var)
            self.ff_pipe.ff.update_parameters()
            # print getattr(self.ff_pipe.ff, key)   # for debugging

    # -- Button actions -- #
    def reset_params(self):
        """Resets parameters to their initial settings."""

        # Brightness, Contrast, Gamma Correction
        self.slContrast.setValue(self.contrast_0)
        self.spnContrast.setValue(self.contrast_0)
        setattr(self.ff_pipe, 'contrast', self.contrast_0)

        self.slBrightness.setValue(self.brightness_0)
        self.spnBrightness.setValue(self.brightness_0)
        setattr(self.ff_pipe, 'brightness', self.brightness_0)

        self.slGamma.setValue(self.gamma_0)
        self.spnGamma.setValue(self.gamma_0)
        setattr(self.ff_pipe, 'gamma', self.gamma_0)

        # Starburst parameters
        self.spnPupilRays.setValue(self.pupil_n_rays_0)
        setattr(self.ff_pipe.ff, 'pupil_n_rays', self.pupil_n_rays_0)
        self.spnPupilRayLength.setValue(self.pupil_ray_length_0)
        setattr(self.ff_pipe.ff, 'pupil_ray_length', self.pupil_ray_length_0)
        self.spnPupilThresh.setValue(self.pupil_threshold_0)
        setattr(self.ff_pipe.ff, 'pupil_threshold', self.pupil_threshold_0)
        self.spnCRRays.setValue(self.cr_n_rays_0)
        setattr(self.ff_pipe.ff, 'cr_n_rays', self.cr_n_rays_0)
        self.spnCRRayLength.setValue(self.cr_ray_length_0)
        setattr(self.ff_pipe.ff, 'cr_ray_length', self.cr_ray_length_0)
        self.spnCRThresh.setValue(self.cr_threshold_0)
        setattr(self.ff_pipe.ff, 'cr_threshold', self.cr_threshold_0)

        # Number of sobel_filtered frames to average
        self.spnSobelFrame.setValue(self.num_frames_sobel_0)
        setattr(self.ff_pipe, 'num_frames', self.num_frames_sobel_0)

        # Update starburst parameters
        self.ff_pipe.ff.update_parameters()

    def reset_guess(self):
        """reset guess to initial choice from ROI selection"""
        # setattr(self.ff_pipe, 'guess_i', self.guess)
        self.ff_pipe.reset_guess(self.guess_i)

    def show_raw(self):
        """Displays the ROI as the raw image (no adjustment)"""

        # set feature finder to display the raw video only
        setattr(self.ff_pipe, 'showRaw', True)
        setattr(self.ff_pipe, 'showAdjFit', False)
        setattr(self.ff_pipe, 'showFit', False)
        setattr(self.ff_pipe, 'showSobel', False)
        # change button states
        self.btnRawVid.setEnabled(False)
        self.btnRawFit.setEnabled(True)
        self.btnAdjFit.setEnabled(True)
        self.btnSobFit.setEnabled(True)

    def show_raw_fit(self):
        """show the ROI as the raw image with markers for the calculated fit"""

        # set feature finder to display the raw video only
        setattr(self.ff_pipe, 'showRaw', False)
        setattr(self.ff_pipe, 'showFit', True)
        setattr(self.ff_pipe, 'showAdjFit', False)
        setattr(self.ff_pipe, 'showSobel', False)
        # change button states
        self.btnRawVid.setEnabled(True)
        self.btnRawFit.setEnabled(False)
        self.btnAdjFit.setEnabled(True)
        self.btnSobFit.setEnabled(True)

    def show_adj_fit(self):
        """Show ROI as adjusted image with calculated fit."""

        # set feature finder to display the raw video only
        setattr(self.ff_pipe, 'showRaw', False)
        setattr(self.ff_pipe, 'showFit', False)
        setattr(self.ff_pipe, 'showAdjFit', True)
        setattr(self.ff_pipe, 'showSobel', False)
        # change button states
        self.btnRawVid.setEnabled(True)
        self.btnRawFit.setEnabled(True)
        self.btnAdjFit.setEnabled(False)
        self.btnSobFit.setEnabled(True)

    def show_sobel_fit(self):
        """Show ROI as Sobel filtered image with calculated fit."""

        # set feature finder to display the raw video only
        setattr(self.ff_pipe, 'showRaw', False)
        setattr(self.ff_pipe, 'showFit', False)
        setattr(self.ff_pipe, 'showAdjFit', False)
        setattr(self.ff_pipe, 'showSobel', True)
        # change button states
        self.btnRawVid.setEnabled(True)
        self.btnRawFit.setEnabled(True)
        self.btnAdjFit.setEnabled(True)
        self.btnSobFit.setEnabled(False)

    def save(self):
        """Saves image image adjustment parameters to temp_ff_file"""

        # save settings to folder
        print 'Settings file saved to ' + self.temp_image_file
        temp_ff_file = open(self.temp_image_file, 'w')
        temp_ff_file.write('sobel_n_frames ' + str(self.num_frames_sobel) + "\n")
        temp_ff_file.write('pupil_n_rays ' + str(self.pupil_n_rays) + "\n")
        temp_ff_file.write('pupil_ray_length ' + str(self.pupil_ray_length) + "\n")
        temp_ff_file.write('pupil_threshold ' + str(self.pupil_threshold) + "\n")
        temp_ff_file.write('cr_n_rays ' + str(self.cr_n_rays) + "\n")
        temp_ff_file.write('cr_ray_length ' + str(self.cr_ray_length) + "\n")
        temp_ff_file.write('cr_threshold ' + str(self.cr_threshold) + "\n")
        temp_ff_file.write('brightness ' + str(self.brightness) + "\n")
        temp_ff_file.write('contrast ' + str(self.contrast) + "\n")
        temp_ff_file.write('gamma ' + str(self.gamma) + "\n")
        temp_ff_file.close()
        self.close()

    def stop(self):
        # stop ff
        setattr(self.ff_pipe, 'stopFlag', True)
        # stop camera
        self.stop_camera()
        # stop display
        self.running = False
        # save
        self.save()
        # kill self
        sys.exit()

    def start(self):
        """Starts threaded feature finder function."""

        if not self.running:
            self.running = True
            # change button
            self.btnStart.setText('Stop')
            # start camera
            self.start_camera()
            # wait a second for queue to populate, then start feature finder
            time.sleep(4)
            self.ff_pipe.startWorkers()

        elif self.running:
            # Stop running
            self.stop()
            self.btnStart.setEnabled(False)

    def start_camera(self):
        """begin live view from eye recording from camera"""

        # set up eye tracking camera and set this instance as the calibrator camera
        if self.cameraID != 'Point_Grey' and self.cameraID != 'recorded':
            try:
                self.CameraReader = CameraReader(int(self.cameraID),
                                                 self.cameraID,
                                                 vidPath=self.vidPath,
                                                 roi=self.ROI,
                                                 display_vid=True,
                                                 image_queue=self.frame_queue)
                self.CameraReader.startReadThread()
            except:
                print "Couldn't start eye tracking camera."
                traceback.print_exc()

        # If no observation camera, keep frame rate high
        elif self.cameraID == 'Point_Grey':
            try:
                mode = 1
                self.CameraReader = runGrasshopper2(mode, vidPath=self.vidPath,
                                                   roi=self.ROI,
                                                   animalName=self.animalName,
                                                   display_vid=True,
                                                   output_queue=self.frame_queue)
                self.CameraReader.startThreads()
            except:
                print "Couldn't start eye tracking camera."
                traceback.print_exc()

        elif self.cameraID == 'recorded':
            try:
                self.CameraReader = VideoReader(self.vidPath,
                                                image_queue=self.frame_queue,
                                                enable_display=False,
                                                roi=self.ROI)
                self.CameraReader.startReadThread()
            except:
                print "Couldn't read video file"

        else:
            print "No eye tracking camera selected."

    def stop_camera(self):
        """Stops cameras"""
        if self.CameraReader is not None and self.cameraID != 'Point_Grey' and \
                self.cameraID != 'recorded':
            self.CameraReader.stopFlag = True
        elif self.CameraReader is not None and self.cameraID == 'Point_Grey':
            self.CameraReader.display_stopFlag = True
        elif self.CameraReader is not None and self.cameraID == 'recorded':
            self.CameraReader.stopFlag = True


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    myWindow = PreviewFitUI(None)
    myWindow.show()
    # do not change to sys.exit(app.exec_()). This will quit the program without
    # shutting things down nicely or saving the data!!!!
    app.exec_()

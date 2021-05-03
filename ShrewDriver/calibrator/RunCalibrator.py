# Run Calibrator: RunCalibrator.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 12/01/2016

# Description: Wrapper class to get cameras and file paths set up for
# calibration sequence. After calibration is complete, cleans up unnecessary
# camera objects to prevent misassignment later.

from __future__ import division
import sys
sys.path.append("..")
from devices.camera_reader import *
try:
    from devices.run_Grasshopper import *
except:

    pass

class RunCalibrator:

    def __init__(self, shrewDriver):
        
        self.stopFlag = False
        self.shrewDriver = shrewDriver
        
        # get UI information from shrewdriver
        self.calibrator_path = self.shrewDriver.calibratorPath
        self.calibrator_file = self.shrewDriver.calibratorFile
        self.cameraID = self.shrewDriver.eyeCameraID
        self.animalName = self.shrewDriver.animalName

        # set camera - will not display continuously, just during relevant sections of calibration
        if self.cameraID != "None" and self.cameraID != 'Point_Grey':

            self.eyeCameraReader = CameraReader(int(self.cameraID), self.animalName, only_roi=True)
            self.shrewDriver.calibrator.camera = self.eyeCameraReader
            self.shrewDriver.calibrator.camera_type = self.cameraID

        elif self.cameraID != "None" and self.cameraID == 'Point_Grey':

            mode = 1
            self.eyeCameraReader = runGrasshopper(mode, animalName=self.animalName, framerate=60, only_roi=True)
            self.shrewDriver.calibrator.camera = self.eyeCameraReader
            self.shrewDriver.calibrator.camera_type = self.cameraID
            self.shrewDriver.calibrator.center_camera_frame = [self.eyeCameraReader.height / 2, self.eyeCameraReader.width / 2]

        # begin
        self.begin()

    def begin(self):
        # Launch StahlLikeCalibrator
        self.shrewDriver.calibrator.calibrate()       
        self.stop_camera()
        self.save()
        
    def save(self):
        self.shrewDriver.calibrator.save_parameters(self.calibrator_path + self.calibrator_file)

    def stop_camera(self):
        # Kills the cameras and deletes any objects related to them
        if self.cameraID != 'Point_Grey':
            self.eyeCameraReader.cap.release()
        else:
            self.eyeCameraReader.c.disconnect()

        del self.eyeCameraReader
        del self.shrewDriver.calibrator.camera

# Run Grasshopper: run_Grasshopper.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 10/27/2016

# Description: Method class for running a Point Grey Grasshopper 3 USB3
# machine vision camera. Accesses proprietary Point Grey FlyCapture2
# library flycapture.c through Python bindings. This class is capable of
# capturing frames from the camera up to its limit of 90 fps with a max
# resolution of 1024 x 1024 px. However, saving video is limited by disk
# write speed. It may be necessary to limit capture frame rate to < 60 fps
# depending on your system.

# Options: Save path, output buffer, shutter speed, brightness, exposure, gain, frame rate

from __future__ import division
import flycapture2 as fc2
from numpy import asarray, array
from Queue import Queue
import threading
import time
import cv2


class runGrasshopper:

    def __init__(self, mode, **kwargs):

        # ------------------ Imaging Parameters ------------------ #
        # Which custom mode we want to be in
        self.mode = mode

        animal = kwargs.get('animalName', '')
        self.animalname = animal + ' - '

        # Image parameters that we want to control
        self.shutter = kwargs.get('shutter', 11)           # [ms]
        self.framerate = kwargs.get('framerate', 60)       # [fps]
        self.gain = kwargs.get('gain', 1.798)              # [dB]
        self.brightness = kwargs.get('brightness', 0.293)  # [%]

        # ------------------ Internal Methods ------------------ #
        # Check if output video path in kwargs. If it is, set save path and
        # method to save the video. If no output video path, the video is not
        # saved, and the save method throws out the frame
        self.vidPath = kwargs.get('vidPath', None)

        if self.vidPath is not None:
            self.save = True
            self._save_method = self._save_vid
        else:
            self.save = False
            self._save_method = self._garbage_collector

        # Set internal queue used for holding acquired frames and metadata
        self.internal_q = Queue()

        # If an output queue is specified
        # This is an externally initiated queue to pass info to the image processing pipeline
        self.out_q = kwargs.get('output_queue', None)

        if self.out_q is not None:
            self._output_method = self._add_to_ext_q
        else:
            self._output_method = self._garbage_collector

        # Initialize counting variable, timestamp, and stop flag
        self.acquire_stopFlag = False
        self.display_stopFlag = False
        self.frame_num = 0
        self.ts = 0

        # ------------------ Get everything set up ------------------ #
        # Setup FlyCapture2 context
        self.c = fc2.Context()

        # find number of connected Point Grey Cameras
        num_cam = self.c.get_num_of_cameras()

        # Only connect if camera is found, and set up imaging parameters
        if num_cam is not None:
            self.c.connect(*self.c.get_camera_from_index(0))

        # --------------- Sets custom acquisition parameters ---------------- #
        # Get custom format7 mode info
        f7 = self.c.get_format7_info(self.mode)

        # ------------- Setup mode to parameters we want to see ------------- #
        self.disply_vid = kwargs.get('display_vid', True)

        # Width and height of image
        self.width = 640
        self.height = 480

        # X and Y offsets to center ROI if not using full frame
        x_diff = (f7[0]['max_width'] - self.width) / f7[0]['offset_h_step_size']
        y_diff = (f7[0]['max_height'] - self.height) / f7[0]['offset_v_step_size']

        # Set format7 parameters
        self.c.set_format7_configuration(1, x_diff, y_diff, self.width, self.height, 4194304)
        # print self.c.get_format7_configuration()

        # Disable automatic image adjustment, turn on these features, and set
        # to absolute parameters so units used for above variables are valid
        for prop in fc2.FRAME_RATE, fc2.SHUTTER, fc2.GAIN, fc2.AUTO_EXPOSURE:
            self.set_feature(prop, auto_manual_mode=False, on_off=True, abs_control=True)

        # Set features as desired in FlyCapture2 SDK
        self.set_feature(fc2.SHUTTER, abs_value=self.shutter)
        self.set_feature(fc2.FRAME_RATE, abs_value=self.framerate)
        self.set_feature(fc2.GAIN, abs_value=self.gain)
        self.set_feature(fc2.BRIGHTNESS, abs_value=self.brightness)

        # ------------------ Set up ROI selection ------------------ #
        # if no selection made, then ROI is full frame
        self.ROI = kwargs.get("roi", [])
        # if we only want to deal with the ROI (both display and save)
        self.only_roi = kwargs.get('only_roi', False)

        # ------------- Set up cv2 VideoWriter object for saving ------------ #
        if self.save:
            # Save as .avi with MJPG encoding
            #fourcc = cv2.cv.CV_FOURCC(*'MJPG')
            fourcc = cv2.VideoWriter_fourcc(*'MJPG') #changed with opencv3
            if not self.only_roi:
                self.video = cv2.VideoWriter(self.vidPath, fourcc,
                                             self.framerate,
                                             (self.width, self.height),
                                             False)
            elif self.only_roi:
                self.video = cv2.VideoWriter(self.vidPath, fourcc,
                                             self.framerate,
                                             (self.ROI[1][0]-self.ROI[0][0], self.ROI[1][1] - self.ROI[0][1]),
                                             False)

    def set_feature(self, prop, **kwargs):
        """
        Args:
            prop:  property to manipulate
            **kwargs: property-specific keywords and values to change

        Returns: Nothing

        Takes property name and value to set arbitrary fc2 features with potentially
        multiple new values
        """

        v = self.c.get_property(prop)
        v.update(kwargs)
        self.c.set_property(**v)

    def get_feature(self, prop):
        """
        Args:
            prop: the flycapture2 property in question

        Returns: absolute value of that flycapture2 property
        """

        v = self.c.get_property(prop)
        return v["abs_value"]

    def start_cap(self):
        """Wrapper for the flycapture2 capture sequence"""
        self.c.start_capture()

    def dequeue(self, **kwargs):
        """
        Args:
            **kwargs: optional flag to return only the image without other info

        Returns: image (as numpy array), frame number, timestamp

        Uses the FC2 retrieve buffer function convert the image byte array to
        a numpy array we can use, then logs the timestamp and frame number.
        """

        im = fc2.Image()
        self.c.retrieve_buffer(im)
        im = asarray(im)
        if 'send' in kwargs:
            return im
        self.ts = time.time()
        self.frame_num += 1
        return im, self.frame_num, self.ts

    def _add_to_ext_q(self, data):
        """Adds data in the form of a dictionary to a queue to be processed
        by image_processing.SubpixelStarburstEyeFeatureFinder via
        ui.preview_fit."""
        self.out_q.put(data)

    def _garbage_collector(self, data):
        """Deletes data from the local frame"""
        del data

    def acquire(self):
        """Threaded function called by self.start_threads() that calls
        self.dequeue(). Takes the frame, frame number, and timestamp, stores
        them in a dictionary, and passes them to an internal queue for either
        display or deletion."""
        while not self.acquire_stopFlag:
            frame, num, ts = self.dequeue()
            self.internal_q.put({'frame': frame.copy(), 'frame_number': num, 'timestamp': ts})

    def _save_vid(self, frame):
        """Writes numpy array to the OpenCV video instance"""
        self.video.write(frame)

    def display_loop(self):
        """Threaded function called by self.start_threads(). Dequeues data from
        self.internal_q and displays the image as a video and saves the movie.
        Is killed when self.display_stopFlag is true.
        """

        while not self.display_stopFlag:
            data = self.internal_q.get()
            frame = data['frame']

            # Restrict frame to roi
            if self.ROI:
                data['frame'] = frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]]

            # If we are viewing videos
            if not self.only_roi and self.disply_vid:
                self._save_method(frame)
                cv2.imshow(self.animalname + 'Eye Tracking Cam', frame)
            elif self.only_roi and self.disply_vid:
                self._save_method(frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])
                cv2.imshow(self.animalname + 'Eye Tracking Cam', frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

            # If we aren't viewing acquired videos
            elif not self.only_roi and not self.disply_vid:
                self._save_method(frame)
            elif self.only_roi and not self.disply_vid:
                self._save_method(frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

            cv2.waitKey(1) & 0xFF
            self._output_method(data)

        self.acquire_stopFlag = True
        time.sleep(0.1)
        self.stopCapture()

    def stopCapture(self):
        """Stops video capture from Point Grey camera, closes the OpenCV video
        instance if necessary, and closes the video display window."""
        if self.save:
            self.video.release()
        self.c.stop_capture()
        self.c.disconnect()
        cv2.destroyWindow(self.animalname + 'Eye Tracking Cam')

    def startThreads(self):
        """Starts image acquisition and display threads"""
        self.acquire_stopFlag = False
        self.display_stopFlag = False
        acquire_thread = threading.Thread(target=self.acquire)
        display_thread = threading.Thread(target=self.display_loop)
        acquire_thread.daemon = True
        display_thread.daemon = True
        self.start_cap()
        acquire_thread.start()
        display_thread.start()


if __name__ == '__main__':

    import sys
    sys.path.append("..")
    from image_processing.ROISelect import *

    mode = 1
    vidPath = 'C:/users/fitzlab1/Desktop/baby_drift.avi'
    im_q = Queue()

    get_roi = ROISelect('Point_Grey')
    get_roi.findROI()
    verticesROI, frame_size, pupil, cr, _ = get_roi.getData()
    gh = runGrasshopper(mode, roi=verticesROI, animalName='Dummy', framerate=60,
                        vidPath=vidPath, output_queue=im_q, only_roi=False)

    gh.startThreads()
    tic = time.time()
    while True:
        data = im_q.get()
        frame = data['frame']
        cv2.imshow('ROI', frame)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    gh.stopFlag = True
    time.sleep(1)
    tot = data['timestamp']-tic
    fr = data['frame_number'] / tot
    print 'Finished with ' + str(gh.frame_num) + ' frames processed in ' + str(tot) + ' seconds.'
    print 'Mean frame rate of ' + str(fr) + ' fps.'

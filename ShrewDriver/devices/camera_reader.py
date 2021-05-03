# camera_reader.py: CameraReader
# Authors: Theo Walker, Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified 07/09/2016

# Description: Class utilizing OpenCV to read a video stream from a webcam. 
# Passing keyword arguments allows for selection of options used for different 
# instances of this class. This class is threaded, with separate threads for 
# video display and saving. Does not capture audio data.

################# System Modules #################
from __future__ import division
import sys
sys.path.append("..")

import cv2
import time
import threading
import traceback

class CameraReader:
    
    def __init__(self, cameraID, animalName, **kwargs):
        self.stopFlag = False
        self.windowName = animalName + ' - Camera (' + str(cameraID) + ")"
        
        # Keyword Arguments - used for different instances of CameraReader
        self.add_axes = kwargs.get("add_axes", False)               # Adds red x and y axes for aligning eye during calibration
        self.save_vid = kwargs.get("save_vid", True)               # Save video or no
        vidPath = kwargs.get("vidPath", None)                       # Path for saving video
        self.out_queue = kwargs.get("image_queue", None)            # output queue for images and frame data
        self.ROI = kwargs.get("roi", [])                            # region of interest
        self.only_roi = kwargs.get("only_roi", False)
        self.disply_vid = kwargs.get('display_vid', True)

        # We only want to save a video if we have a destination for it
        if vidPath is not None:
            self.save_vid = True
        
        #set up frame acquisition, display, and disk writing
        self.cap = cv2.VideoCapture(cameraID)
        self.cap.set(3, 320)
        self.cap.set(4, 240)

        # Frame size and resolution needed to achieve maximum framerate.
        self.readFrame()
        if self.only_roi:
            self.frame = self.frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]]
        rows, cols, channels = self.frame.shape        
        self.half_row = int(rows/2)
        self.half_col = int(cols/2)
        
        if self.save_vid:
            self.frameRate = 20                                             # Set framerate at which video is saved
            #fourcc = cv2.cv.CV_FOURCC(*'MJPG')                              # Save as .avi with XVID encoding
            fourcc = cv2.VideoWriter_fourcc(*'MJPG') #changed with opencv3
            self.video = cv2.VideoWriter(vidPath, fourcc, self.frameRate, (cols, rows))    # set up object to save videos in .avi format
            
        # Initialize variables
        self.timestamp = 0                                               # initialize timestamp
        self.frame_number = 0                                            # initialize frame number          

    def readFrame(self, **kwargs):
        ret, self.frame = self.cap.read()
        
        # Stupid hack to return a frame to the calibrator without running the camera reader thread
        # Color change shouldn't be necessary for B/W camera
        if 'send' in kwargs:
            return cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)

    def captureFrame(self):
        self.readFrame()
        rows, cols, channels = self.frame.shape
        
        # Once in a while, a bad frame comes off the camera. Skip it.
        if rows == 0 or cols == 0:
            return
        self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)

        if self.add_axes:
            cv2.line(self.frame, (0, self.half_row), (cols, self.half_row), (0,0,255))
            cv2.line(self.frame, (self.half_col, 0), (self.half_col, rows), (0,0,255))   

        if not self.only_roi and self.disply_vid:
            cv2.imshow(self.windowName, self.frame)
        elif self.only_roi and self.disply_vid:
            cv2.imshow(self.windowName, self.frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

        # If we are saving the video
        if self.save_vid and not self.only_roi:
            self.video.write(self.frame)
        elif self.save_vid and self.only_roi:
            self.video.write(self.frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

        cv2.waitKey(1) & 0xFF       #pauses 1ms, allows frame to display

    def acquire(self):
        #thread function, loops capture until stopped
        #blocking happens automatically at self.cap.read() so this won't consume
        #much CPU. No need for a sleep() call.

        while True:
            # Check if stop flag has been thrown
            if self.stopFlag:
                self.stopCapture()
                break            
            
            self.captureFrame() 
                
            # Built-in openCV functions are not supported for webcam video streams   
            self.frame_number += 1                                           # log number of frames acquired      
            self.timestamp = time.time()                                     # log absolute timestamp of frame in
            
            # If we have a queue for the data, put it here
            if self.out_queue is not None:
                # Save frame and necessary data to a dictionary     
                data = {'frame': self.frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]], 'frame_number': self.frame_number, 'timestamp': self.timestamp}            
                self.out_queue.put(data)
        
    def startReadThread(self):
        self.stopFlag = False
        display_thread = threading.Thread(target = self.acquire)
        display_thread.daemon = True
        display_thread.start()

    def stopCapture(self):
        # When everything done, release the capture
        if self.save_vid:
            self.video.release()
            cv2.waitKey(1) & 0xFF
        self.cap.release()
        cv2.destroyAllWindows()    
    
"""Test Code"""    
if __name__ == '__main__':
    from Queue import Queue
    from image_processing.ROISelect import *
    
    #set up CameraReader object
    cameraID = 0
    savePath = 'C:/users/fitzlab1/Desktop/video' + str(cameraID) + '.avi'
    im_q = Queue()   

    # get_roi = ROISelect(cameraID)
    # get_roi.findROI()
    # verticesROI, frame_size, pupil, cr = get_roi.getData()
    cr = CameraReader(cameraID, "Dummy", vidPath=savePath)

    #start it running
    cr.startReadThread()
    
    #keep busy while it runs
    startTime = time.time()
    while time.time() - startTime < 10:
        pass
    
    #stop it, and wait for it to shut down nicely
    cr.stopFlag = True
    time.sleep(1)
    print "done!"
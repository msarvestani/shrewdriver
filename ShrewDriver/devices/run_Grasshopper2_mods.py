# Run Grasshopper v.2: run_Grasshopper2.py
# Author: Matthew McCann (@mkm4884)
# Max Planck Florida Institute for Neuroscience
# Last Modified: 05/24/2016

# Description: Method class for running a Point Grey Grasshopper 3 USB3
# machine vision camera. Accesses proprietary Point Grey FlyCapture2
# library flycapture.c through python bindings. This class is capable of
# capturing frames from the camera up to its limit of 90 fps with a max
# resolution of 1024 x 1024 px. However, saving video is limited by disk
# write speed. It may be necessary to limit capture frame rate to < 60 fps
# depending on your system.

# Options: Save path, output buffer, shutter speed, brightness, exposure, gain, frame rate

import cv2
import PyCapture2
from numpy import asarray, array, reshape, uint8, random, mat
from Queue import Queue
import threading
import time

class runGrasshopper2:

    def __init__(self, mode, **kwargs):

        # ------------------ Imaging Parameters ------------------ #
        # Which custom mode we want to be in
        self.mode = mode

        animal = kwargs.get('animalName', '')
        self.animalname = animal + ' - '

        # Image parameters that we want to control. These are dependent on the animal.
        # May need to be tweaked from animal to animal, and add animals as needed.
        if animal.lower() == "qbert":
            self.shutter = kwargs.get('shutter', 11)  # [ms]
            self.framerate = kwargs.get('framerate', 60)  # [fps]
            self.gain = kwargs.get('gain', 0.0)  # [dB]
            self.exposure = kwargs.get('exposure', 0.970)  # [EV]
            self.brightness = kwargs.get('brightness', 0.293)  # [%]
        else:
            self.shutter = kwargs.get('shutter', 11)  # [ms]
            self.framerate = kwargs.get('framerate', 60)  # [fps]
            self.gain = kwargs.get('gain', 1.798)  # [dB]
            self.exposure = kwargs.get('exposure', 0.970)  # [EV]
            self.brightness = kwargs.get('brightness', 0.293)  # [%]

        # ------------------ Internal Methods ------------------ #
        # Check if output video path in kwargs. If it is, set save path and method to save the video
        # If no output video path, the video is not saved, and the save method throws out the frame
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
        # This is an externally initiated queue to pass ifo to the image processing pipeline
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
        # Ensure sufficient cameras are found
        bus = PyCapture2.BusManager()
        numCams = bus.getNumOfCameras()
        if not numCams:
            print "Insufficient number of cameras. Exiting..."
            exit()

        # Select camera on 0th index
        self.c = PyCapture2.Camera()
        uid = bus.getCameraFromIndex(0)
        self.c.connect(uid)

        # ------------------ Sets custom acquisition parameters ------------------ #
        # Get custom format7 mode info
        f7, _ = self.c.getFormat7Info(self.mode)

        # ------------------ Setup mode to parameters we want to see ------------------ #
        # Width and height of image
        self.width = 640
        self.height = 480

        # X and Y offsets to center ROI if not using full frame
        x_diff = (f7.maxWidth - self.width) / f7.offsetHStepSize
        y_diff = (f7.maxHeight - self.height) / f7.offsetVStepSize

        # Set format7 parameters
        fmt7imgSet = PyCapture2.Format7ImageSettings(1, x_diff, y_diff, self.width, self.height, PyCapture2.PIXEL_FORMAT.RAW8)
        fmt7pktInf, isValid = self.c.validateFormat7Settings(fmt7imgSet)
        if not isValid:
            print "Format7 settings are not valid!"
            exit()
        self.c.setFormat7ConfigurationPacket(fmt7pktInf.maxBytesPerPacket, fmt7imgSet)
        f7_config = self.c.getFormat7Configuration()

        # Disable automatic image adjustment, turn on these features, and set to absolute parameters
        # so units used for above variables are valid. Set features as desired in FlyCapture2 SDK
        props = PyCapture2.PROPERTY_TYPE()
        self.c.setProperty(type=PyCapture2.PROPERTY_TYPE.SHUTTER, autoManualMode=False, onOff=True, absControl=True, absValue=self.shutter)
        self.c.setProperty(type=PyCapture2.PROPERTY_TYPE.FRAME_RATE, autoManualMode=False, onOff=True, absControl=True, absValue=self.framerate)
        self.c.setProperty(type=PyCapture2.PROPERTY_TYPE.GAIN, autoManualMode=False, onOff=True, absControl=True, absValue=self.gain)
        self.c.setProperty(type=PyCapture2.PROPERTY_TYPE.AUTO_EXPOSURE, autoManualMode=False, onOff=True, absControl=True, absValue=self.exposure)
        #self.c.setProperty(type=PyCapture2.PROPERTY_TYPE.BRIGHTNESS, absValue=self.brightness)

        # Enable camera embedded timestamp
        self.enableEmbeddedTimeStamp(self.c, True)

        # Check config and grab mode

        config = PyCapture2.Config()
        gmode = PyCapture2.GRAB_MODE()
        self.c.setConfiguration(grabMode=gmode.DROP_FRAMES)

        # ------------------ Set up ROI selection ------------------ #
        self.display_vid = kwargs.get('display_vid', True)
        # if no selection made, then ROI is full frame
        self.ROI = kwargs.get("roi", [])
        # if we only want to deal with the ROI (both display and save)
        self.only_roi = kwargs.get('only_roi', False)


        # ------------------ Set up cv2 VideoWriter object for saving ----------------- #
        self.video = PyCapture2.FlyCapture2Video()

        if self.save:
            if not self.only_roi:
                self.video.AVIOpen(self.vidPath, self.framerate)
            elif self.only_roi:
                self.video = cv2.VideoWriter(self.vidPath, fourcc, self.framerate, (self.ROI[1][0]-self.ROI[0][0], self.ROI[1][1]-self.ROI[0][1]), False)


    def enableEmbeddedTimeStamp(self, cam, enableTimeStamp):
        embeddedInfo = cam.getEmbeddedImageInfo()
        if embeddedInfo.available.timestamp:
            cam.setEmbeddedImageInfo(timestamp=enableTimeStamp)
            if (enableTimeStamp):
                print "\nTimeStamp is enabled.\n"
            else:
                print "\nTimeStamp is disabled.\n"


    def start_cap(self):
        self.c.startCapture()

    def dequeue(self, **kwargs):
        #image = self.cam.retrieveBuffer()
        image = self.c.retrieveBuffer()
        im = reshape(array(image.getData(), dtype=uint8), (480, 640))

        # self.ts = self.ts.cycleSeconds
        # timestamp info is weird here, but let's go anyways
        #self.ts = image.getTimeStamp()
        #self.ts = self.ts.cycleSeconds


        if 'send' in kwargs:
            return im
        self.ts = time.time()
        self.frame_num += 1
        return im, self.frame_num,self.ts, image

    def _add_to_ext_q(self, data):
        self.out_q.put(data)

    def _garbage_collector(self, data):
        del data

    def acquire(self):
        while not self.acquire_stopFlag:
            frame, num, ts, image = self.dequeue()
            self.internal_q.put({'frame': frame, 'frame_number': num, 'timestamp': ts, 'image': image})

    def _save_vid(self, image):
        #self.video.write(frame)
        self.video.append(image)

    def stopCapture(self):
        if self.save:
            #self.video.release()
            self.video.close()
        self.c.stopCapture()
        self.c.disconnect()
        cv2.destroyWindow(self.animalname + 'Eye Tracking Cam')

    def startThreads(self):
        self.acquire_stopFlag = False
        self.display_stopFlag = False
        acquire_thread = threading.Thread(target=self.acquire)
        display_thread = threading.Thread(target=self.display_loop)
        acquire_thread.daemon = True
        display_thread.daemon = True
        self.start_cap()
        print 'Starting camera...'
        acquire_thread.start()
        print 'Starting camera display...'
        display_thread.start()

    def display_loop(self):

        while not self.display_stopFlag:
            data = self.internal_q.get()
            frame = data['frame']
            image = data['image']

            # frame = random.rand(480, 640) * 255
            # data['frame'] = frame
            # Restrict frame to roi
            if self.ROI:
                data['frame'] = frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]]

            # If we are viewing videos
            if not self.only_roi and self.display_vid:
                self._save_method(image)
                cv2.imshow(self.animalname + 'Eye Tracking Cam', frame)
            elif self.only_roi and self.display_vid:
                self._save_method(frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])
                cv2.imshow(self.animalname + 'Eye Tracking Cam', frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

            # If we aren't viewing acquired videos
            elif not self.only_roi and not self.display_vid:
                self._save_method(image)
            elif self.only_roi and not self.display_vid:
                self._save_method(frame[self.ROI[0][1]:self.ROI[1][1], self.ROI[0][0]:self.ROI[1][0]])

            cv2.waitKey(0) & 0xFF
            self._output_method(data)

        self.acquire_stopFlag = True
        time.sleep(0.1)
        self.stopCapture()

if __name__ == '__main__':

    import sys
    sys.path.append("..")
    from image_processing.ROISelect import *

    mode = 1
    vidPath = 'C:/users/mccannm/Desktop/newvid.avi'
    im_q = Queue()

    get_roi = ROISelect('Point_Grey')
    get_roi.findROI()
    verticesROI, frame_size, pupil, cr, _ = get_roi.getData()
    gh = runGrasshopper2(mode, animalName='Dummy', framerate=60, vidPath=None, output_queue=im_q, only_roi=False)

    gh.startThreads()
    tic = time.time()
    while True:
        data = im_q.get()
      #  print(time.ctime(data['timestamp']))
        frame = data['frame']

        cv2.imshow('ROI', frame)
        key = cv2.waitKey(0) & 0xFF
        if key == ord('q'):
            break

    gh.stopFlag = True
    time.sleep(1)

    tot = data['timestamp']-tic
    fr = data['frame_number'] / tot
    print 'Finished with ' + str(gh.frame_num) + ' frames processed in ' + str(tot) + ' seconds.'
    print 'Mean frame rate of ' + str(fr) + ' fps.'

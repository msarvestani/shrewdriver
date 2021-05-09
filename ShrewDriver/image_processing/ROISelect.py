# ROISelect.py: ROI Select
# Author: Matthew McCann (@mkm60)
# Max Planck Florida Institute for Neuroscience (MPFI)
# Created: 09/21/2016
# Last Modified: 03/09/2017

# Description: Region of Interest (ROI) selection using OpenCV and mouse clicks.
# Press enter once camera is correctly adjusted.
# Simply click and drag to select ROI. Press R to reset selection, and enter to
# crop, and ESC to exit. Once ROI is selected, press ENTER to select pupil and
# corneal LED reflection (if present). After pupil and CR identified, the user
# can click to fit an ellipse to the edge of the eyeball to create a mask used
# during image adjustment.

# Lightly modified from code and comments by Adrian Rosebrock and others at
# http://www.pyimagesearch.com/2015/03/09/capturing-mouse-click-events-with-python-and-opencv/

# Click to make polygon adapted from
# http://stackoverflow.com/questions/37099262/drawing-filled-polygon-using-mouse-events-in-open-cv-using-python

import sys
import cv2
from numpy import zeros_like, vstack, concatenate, asanyarray, reshape, array
sys.path.append("..")
from devices.camera_reader import *
try:
    from devices.run_Grasshopper2 import *
except:

    pass
from devices.video_file_reader import *


class ROISelect:

    def __init__(self, cameraID, **kwargs):
        """
        Args:
            cameraID: specified as either string ('Point_Grey', 'video', or a
                      number) to read from the correct device.
            **kwargs: 'add_axes' adds axes through the middle of the X and Y
                       dimensions of the frame, like crosshairs
        """

        # setup super basic camera reader to grab frames
        if cameraID == 'Point_Grey':
            self._get_image = self.loopImage
            self.cr = runGrasshopper2(1)
            self.cam_type = cameraID
            self.cr.start_cap()

        elif cameraID == 'video':
            self.cam_type = cameraID
            self._get_image = self.get_frames
            path = kwargs['vidPath']
            self.vr = VideoReader(path, enable_display=False)
            self.frame = self.vr.readFrame(send=1)

        else:
            self._get_image = self.loopImage
            self.cr = CameraReader(int(cameraID), 'ROI')
            self.cam_type = 'Webcam'

        self.camera_on = True

        # a boolean to see if we want to add crosshairs to the image for calibration
        self.add_axes = kwargs.get('add_axes', False)

        # a variable to store the difference between the edges of the roi and the frame
        self.roi_diff = []

        # initialize the list of reference points and boolean indicating
        # whether cropping is being performed or not
        self.refPt = []
        self.sel_rect_endpoint = []
        self.cropping = False

        # initialize a list of coordinates for pupil and CR center
        # these values will be in reference to the cropped image
        self.pupil_seed = []
        self.cr_seed = []
        self.selection = False
        self.selection_loop = True
        self.poly_select = False
        self.current = (0, 0)
        self.elli_pts = []
        self.empty_roi = None

    def click_and_crop(self, event, x, y, flags, param):
        """
        Args:
            event: OpenCV mouse event performed on the window
            x: X coordinate (int)
            y: Y coordinate (int)
            flags: needed by OpenCV for some reason, unsure why
            param: needed by OpenCV for some reason, unsure why

        Returns: Nothing, but assigns values to self
        """

        # if the left mouse button was clicked, record the starting (x, y)
        # coordinates and indicate that cropping is being performed
        if event == cv2.EVENT_LBUTTONDOWN:
            self.refPt = [(x, y)]
            self.cropping = True

        # check to see if the left mouse button was released
        elif event == cv2.EVENT_LBUTTONUP:
            # record the ending (x, y) coordinates and indicate that the
            # cropping operation is finished
            self.refPt.append((x, y))
            self.cropping = False

            # draw a rectangle around the region of interest
            cv2.rectangle(self.image, self.refPt[0], self.refPt[1],
                          (0, 255, 0), 2)
            cv2.imshow("frame", self.image)

        elif event == cv2.EVENT_MOUSEMOVE and self.cropping:
            self.sel_rect_endpoint = [(x, y)]

    def click_to_select(self, event, x, y, flags, param):
        """
        Args:
            event: OpenCV mouse event performed on the window
            x: X coordinate (int)
            y: Y coordinate (int)
            flags: needed by OpenCV for some reason, unsure why
            param: needed by OpenCV for some reason, unsure why

        Returns: Nothing, but assigns values to self. Displays the new frame.
        """

        # if left mouse button clicked, record selection point
        if event == cv2.EVENT_LBUTTONDOWN and self.selection == False:
            self.pupil_seed = [(y, x)]  # Put in [row, col] format
            cv2.circle(self.roi, (x, y), 3, 255, 1)  # opencv draws in x,y
            cv2.imshow('ROI', self.roi)

        elif event == cv2.EVENT_LBUTTONDOWN and self.selection == True:
            self.cr_seed = [(y, x)]  # Put in [row, col] format
            cv2.circle(self.roi, (x, y), 3, 255, 1)     # opencv draws in x,y
            cv2.imshow('ROI', self.roi)

    def mouse_over_polygon(self, event, x, y, flags, param):
        """
        Args:
            event: OpenCV mouse event performed on the window
            x: X coordinate (int)
            y: Y coordinate (int)
            flags: needed by OpenCV for some reason, unsure why
            param: needed by OpenCV for some reason, unsure why

        Returns: Nothing, but assigns values to self
        """
        if self.poly_select:
            return

        # Track current mouse position to see real-time line
        if event == cv2.EVENT_MOUSEMOVE:
            self.current = (x, y)
        # On click, append coordinate to self.elli_pts and record current frame
        elif event == cv2.EVENT_LBUTTONDOWN:
            self.roi_one_back = self.roi.copy()
            self.elli_pts.append((x, y))

    def loopImage(self):
        """Simple loop to continuously display still frame
        """
        # keep looping until the ENTER key is pressed
        while self.camera_on:

            # load the image, clone it
            if self.cam_type == 'Webcam':
                self.image = self.cr.readFrame(send=True)

            elif self.cam_type == 'Point_Grey':
                #self.image = fc2.Image()# this only works with run_Grasshopper
                self.image = self.cr.c.retrieveBuffer()
                self.image = reshape(array(self.image.getData(), dtype=uint8), (self.image.getRows(), self.image.getCols()))

            self.clone = self.image.copy()
            frame = self.image.copy()

            if self.add_axes:
                rows, cols = frame.shape
                half_row = int(rows / 2)
                half_col = int(cols / 2)
                cv2.line(frame, (0, half_row), (cols, half_row), (0, 0, 255))
                cv2.line(frame, (half_col, 0), (half_col, rows), (0, 0, 255))

            cv2.imshow('Live Feed', frame)
            key = cv2.waitKey(1) & 0xFF

            # If ENTER is pressed
            if key == 13:
                if self.cam_type == 'Webcam':
                    self.cr.stopCapture()
                elif self.cam_type == 'Point_Grey':
                    self.cr.c.stopCapture()


                self.camera_on = False
                cv2.destroyWindow('Live Feed')
                cv2.namedWindow("frame")
                cv2.setMouseCallback("frame", self.click_and_crop)

            elif key == 27:
                return

        rows, cols = self.image.shape
        self.frame_size = [int(cols), int(rows)]

    def get_frames(self):
        """Sets self.image, but keeps a copy of the old frame in case of a reset"""
        self.image = self.frame
        self.clone = self.image.copy()

        rows, cols = self.image.shape
        self.frame_size = [int(cols), int(rows)]

        cv2.namedWindow("frame")
        cv2.setMouseCallback("frame", self.click_and_crop)

    def findROI(self):
        """Click and drag to select ROI. Press R to reset selection,
        ESC to abort, and Enter to crop.

        This is the function called to start the ROI Selection sequence.
        """
        self._get_image()

        while True:

            # display the image and wait for a keypress
            if not self.cropping:
                cv2.imshow('frame', self.image)
            elif self.cropping and self.sel_rect_endpoint:
                rect_cpy = self.image.copy()
                cv2.rectangle(rect_cpy, self.refPt[0], self.sel_rect_endpoint[0],
                              (0, 255, 0), 1)
                cv2.imshow('frame', rect_cpy)

            key2 = cv2.waitKey(1) & 0xFF

            # if the 'r' key is pressed, reset the cropping region
            if key2 == ord('r'):
                self.refPt = []
                self.image = self.clone.copy()
                print "Reset ROI selection"

            # if the 'enter' key is pressed, break from the loop
            elif key2 == 13:
                print "ROI selected"
                break

            # if ESC is pressed
            elif key2 == 27:
                self.refPt = []
                print "No ROI selected."
                return

        # if there are two reference points, then crop the region of interest
        # from the image and display it
        if len(self.refPt) == 2:
            # Sort points by minimum to always get correct rectangle
            ix = self.refPt[0][0]
            iy = self.refPt[0][1]
            x = self.refPt[1][0]
            y = self.refPt[1][1]
            # set bounding box by mouse move
            self.refPt = [(min(ix, x), min(iy, y)), (max(ix, x), max(iy, y))]
            # stick to [rows, columns] convention (Y, X)
            self.roi_diff = [(min(iy, y)), (min(ix, x))]

            self.roi = self.clone[self.refPt[0][1]:self.refPt[1][1],
                                  self.refPt[0][0]:self.refPt[1][0]]
            self.roi_clone = self.roi.copy()
            cv2.destroyWindow('frame')

            # Select the pupil and CR centers
            self.findPupilCR()
            # Fit an ellipse to exclude unnecessary regions of the ROI
            # surrounding the eye
            self.findEyeEllipse()

    def findPupilCR(self):
        """
        Method following the selection of a rectanglar ROI from self.findROI
        Asks the user to first select the rough pupil center with a mouse click,
        confirm it by pressing ENTER, or reset it by pressing 'r'. The user then
        selects the rough corneal reflection (CR) in the same way.
        """
        cv2.namedWindow("ROI")
        # Create window where the self.click_to_select method applies
        cv2.setMouseCallback("ROI", self.click_to_select)

        while True:
            cv2.imshow("ROI", self.roi)
            key = cv2.waitKey(1) & 0xFF

            # Pupil selection logic
            if key == 13 and self.selection == False:
                # If ENTER is pressed
                self.roi_clone = self.roi.copy()
                key = None
                self.selection = True
                print "Pupil center selected"
            elif key == ord('r') and self.selection == False:
                # If 'r' is pressed
                self.pupil_seed = []
                self.roi = self.roi_clone.copy()
                print "Reset pupil center selection"

            # CR selection logic
            if key == 13 and self.selection == True:
                print "CR center selected"
                self.roi_clone = self.roi.copy()
                break
            elif key == ord('r') and self.selection == True:
                self.cr_seed = []
                self.roi = self.roi_clone.copy()
                print "Reset CR center selection"
            elif key == 27:
                self.cr_seed = []
                print "No CR selected"
                break

        self.empty_roi = self.roi.copy()

    def findEyeEllipse(self):
        """
        The final method that gets called to fit a bounding ellipse around the
        eye. The user clicks to set vertices on an n-sided polygon. Pressing
        'r' resets the most recently selected point. Once enough points are
        selected, the user presses ENTER to fit the ellipse. If the fit is
        satisfactory, the user presses ENTER to confirm the fit, and all windows
        close. If the fit is bad, pressing 'r' resets all points and the user
        tries again.
        """
        cv2.imshow('ROI', self.roi)
        # Create window where the self.mouse_over_polygon method applies
        cv2.setMouseCallback("ROI", self.mouse_over_polygon)
        is_fit = False
        is_confirmed = False

        while not self.poly_select:
            cv2.imshow("ROI", self.roi)
            key = cv2.waitKey(1) & 0xFF

            if len(self.elli_pts) > 0 and not is_fit:
                self.roi = self.roi_clone.copy()
                # Draw all the current polygon segments
                cv2.polylines(self.roi, array([self.elli_pts]), False, 255, 1)
                # And  also show what the current segment would look like
                cv2.line(self.roi, self.elli_pts[-1], self.current, 255)

            # Want to see ellipse on enter hit
            if key == 13 and len(self.elli_pts) >= 5 and not is_fit \
                    and not is_confirmed and not self.poly_select:
                is_fit = True
                self.roi = self.empty_roi.copy()
                self.ellipse = cv2.fitEllipse(array([self.elli_pts]))
                cv2.ellipse(self.roi, self.ellipse, 255, 1)

            # if the user fucks up
            elif key == 13 and len(self.elli_pts) < 5 and not is_fit \
                    and not is_confirmed and not self.poly_select:
                pass

            # Confirm ellipse
            elif key == 13 and not self.poly_select and not is_confirmed and is_fit:
                is_confirmed = True
                self.poly_select = True
                print 'Eye mask selected'
                break

            # Line reset
            elif key == ord('r') and not self.poly_select and not is_fit \
                    and not is_confirmed:
                if len(self.elli_pts) > 1:
                    del self.elli_pts[-1]
                    self.roi = self.roi_one_back.copy()
                else:
                    del self.elli_pts[-1]
                    self.roi = self.empty_roi.copy()

            # ellipse reset
            elif key == ord('r') and not self.poly_select and is_fit \
                    and not is_confirmed:
                is_fit = False
                self.roi = self.empty_roi.copy()
                del self.elli_pts[:], self.ellipse

        # close all open windows
        if self.cam_type == 'Webcam':
            self.cr.cap.release()
        elif self.cam_type == 'Point_Grey':
            self.cr.c.disconnect()
        elif self.cam_type == 'video':
            self.vr.cap.release()

        cv2.destroyAllWindows()

    def create_eyeball_mask(self):
        """
        Depreciated.
        """
        pup_coords = self.pupil_seed
        im_val_pup = self.roi[pup_coords[0][0], pup_coords[0][1]]
        _, im1 = cv2.threshold(self.roi, int(im_val_pup * 0.9), 255,
                               type=cv2.THRESH_TOZERO_INV)
        im2 = cv2.Canny(im1,  int(im_val_pup * 0.9), 110)
        contours, heirarchy = cv2.findContours(im2.copy(), cv2.RETR_EXTERNAL,
                                               method=cv2.CHAIN_APPROX_NONE)
        edges = []
        # only want long contours
        for contour in contours:
            if contour.size > 100:
                c = vstack(contour)
                edges.append(c)
        # cv2.drawContours(im, edges[1:], -1, 255, 1)
        if edges:
            tot_e = concatenate(edges[1:], axis=0)
            self.ellipse = cv2.fitEllipse(tot_e)
            cv2.ellipse(self.roi, self.ellipse, 255, 1)

    def getData(self):
        """
        Returns: reference points, distance between edges of ROI and original
        image, pupil coordinates, cr coordinates, and the ellipse mask.
        """
        return self.refPt, self.roi_diff, self.pupil_seed, self.cr_seed, self.ellipse


if __name__ == '__main__':
    cameraID = 'video'
    cameraID = 'Point_Grey'
    roi = ROISelect(cameraID, vidPath='C:\Users\mccannm\Documents\Data\Qbert/t00028/t00028\Qbert_t00028_conv.avi')
    roi.findROI()
    refPt, roi_diff, pupil, cr, _ = roi.getData()
    if refPt == [] and roi_diff == []:
        print "ROI selection aborted"
    else:
        print refPt
        print roi_diff
        print pupil
        print cr


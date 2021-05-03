#
#  StahlLikeCalibrator.py
#  EyeTracker
#
#  Created by David Cox on 12/2/08.
#  Copyright (c) 2008 Harvard University. All rights reserved.
#

from math import *
from numpy import *
from scipy import *
import scipy.optimize
from scipy import stats
import cPickle as pkl
import logging
import cv2
import sys
sys.path.append('..')
from image_processing.ROISelect import *


class StahlLikeCalibrator:

    uncalibrated = 0
    pupil_only_uncalibrated = 1
    pupil_only = 2
    full_calibration = 3

    no_led = -1
    both_leds = -2

    def __init__(self, camera, feature_finder, **kwargs):
        # handles to real-world objects
        self.camera = camera
        self.camera_type = None
        self.feature_finder = feature_finder

        # These are dummy variables to be used instead of a real LED controller
        self.current_led = None
        self.top_led = 0
        self.side_led = 1
        self.both_leds = 2

        # Not sure about this setting
        self.default_pixels_per_mm = kwargs.get('default_pixels_per_mm', 17.96)
        # May need to change for shrew dimensions
        self.default_Rp = kwargs.get("default_Rp", 3.2 * self.default_pixels_per_mm)

        self.ui_queue = kwargs.get("ui_queue", None)
        # Note for coordinates, [row, col] = [y, x] convention is followed
        self.x_image_axis = kwargs.get("x_image_axis", 1)
        self.y_image_axis = kwargs.get("y_image_axis", 0)
        self.x_stage_axis = kwargs.get("x_stage_axis", 'x axis')
        self.x_stage_direction = kwargs.get("x_stage_direction", -1)
        self.y_stage_axis = kwargs.get("y_stage_axis", 'y axis')
        self.y_stage_direction = kwargs.get("y_stage_direction", -1)
        self.r_stage_direction = kwargs.get("r_stage_direction", 1)
        self.d_guess = kwargs.get("d_guess", 380)
        # angle of camera rotation for pseudo-eye rotation in degrees
        self.jog_angle = kwargs.get("jog_angle", 15.)
        self.z_delta = kwargs.get("z_delta", 1.)
        self.cr_diff_threshold = kwargs.get("cr_diff_threshold", 0.1)
        # 0.5 * max range of uncertainty of distance from cam to target
        self.d_halfrange = kwargs.get("d_halfrange", 50.)
        # a quantum of stage displacement in millimeters
        self.Dx = kwargs.get("Dx", 1)

        # In pixels. Value needs to be determined. Used as a metric of how well
        # the cr is aligned with axes.
        self.default_cr_positions = {}
        self.cr_tolerances = 5    # [px]
        self.pos_guess = {"pupil_position": array([0, 0]),
                          "cr_position": array([0, 0])
                          }

        self.axis_dirs = ['HORIZONTAL', 'VERTICAL']
        self.vertical_dirs = ['UP', 'DOWN']
        self.horizontal_dirs = ['to the LEFT', 'to the RIGHT']

        self.calibration_status = 0

        # initialize internal calibration parameters
        self.pupil_cr_diff = None
        self.zoom_factor = None        
        self.n_calibration_samples = 5
        self.offset = None
        self.d = self.d_guess         # distance to center of corneal curvature
        self.Rp = None                # radius to pupil, from center of corneal curvature
        self.Rp_mm = None
        self.y_equator = None
        self.y_topCR_ref = None
        self.pixels_per_mm = None
        self.center_camera_frame = None  # center of the camera frame
        
        # record position of stages
        self.x_position = 0
        self.y_position = 0
        self.z_position = 0

        self.quiet = 1

        self.CompLensDistor = CompensateLensDistorsion()

    @property
    def info(self):
        """Properties available as a class attribute"""
        info = {'distance': self.d,
                'Rp': self.Rp,
                'Rp_mm': self.Rp_mm,
                'y_equator': self.y_equator,
                'y_topCR_ref': self.y_topCR_ref,
                'pixels_per_mm': self.pixels_per_mm,
                'n_calibration_samples': self.n_calibration_samples,
                }

        # remove all None values
        r = {}
        for k, v in info.iteritems():
            if v is not None:
                r[k] = v

        # print "Cleaned Info", r
        return r

    def release(self):
        # Release the camera
        self.camera = None

    @property
    def calibrated(self):
        return (self.d != None and self.Rp != None and self.y_equator != None and self.y_topCR_ref != None )

    def save_parameters(self, filename):
        # -------- From self.info ---------------
        calibrator_info = {'distance': self.d,
                           'Rp': self.Rp,
                           'Rp_mm': self.Rp_mm,
                           'y_equator': self.y_equator,
                           'y_topCR_ref': self.y_topCR_ref,
                           'pixels_per_mm': self.pixels_per_mm,
                           'n_calibration_samples': self.n_calibration_samples,
                           'x_position': self.x_position,
                           'y_position': self.y_position,
                           'z_position': self.z_position
                           }
            
        d = dict(calibrator=calibrator_info) 

        with open(filename, 'w') as f:
            pkl.dump(d, f)

    def check_parameters(self, p):
        
        if 'calibrator' not in p:
            print "calibrator missing"
            return False
        for k in ('distance', 'Rp', 'Rp_mm', 'y_equator', 'y_topCR_ref', 'pixels_per_mm'):
            if k not in p['calibrator']:
                logging.error("calibrator missing: calibrator.%s" % k)
                return False
        return True

    def set_parameters(self, parameters):
        # check info
        print "Checking parameters"
        if not self.check_parameters(parameters):
            return False
        
        print "Setting parameters"
        c = parameters['calibrator']
        self.d = c['distance']
        self.Rp = c['Rp']
        self.pixels_per_mm = c['pixels_per_mm']
        self.Rp_mm = self.Rp / self.pixels_per_mm
        self.y_equator = c['y_equator']
        self.y_topCR_ref = c['y_topCR_ref']
        self.y_position = float(c['y_position'])
        self.z_position = float(c['z_position'])
        
        if self.Rp_mm != c['Rp_mm']:
            logging.error("Calculated Rp_mm[%g] != loaded [%g]" % (self.Rp_mm, c['Rp_mm']))
            return False

        return True

    def load_parameters(self, filename):
        print("Loading calibration file from: %s" % filename)
        d = None
        with open(filename, 'r') as f:
            d = pkl.load(f)

        if d is not None:
            if not self.set_parameters(d):
                print "Failed to set calibration parameters in: %s" % filename
                return
            
            # Set stages and get ready for image acquisition
            raw_input("Move x_axis of stage to %0.f mm. Press enter to continue setup." % self.x_position)
            raw_input("Move y_axis of stage to %0.f mm. Press enter to continue setup." % self.y_position)
            raw_input("Move z_axis of stage to %0.f mm. Press enter to continue setup." % self.z_position)
            raw_input("Set rotation stage to ZERO degrees. Press enter to continue.")
            raw_input("Turn on top LED. Press enter to continue.")

            self.calibration_status = 1

        else:
            self.calibration_status = 0
            return

    def report_set_gaze_values(self):

        # Acquire first n gaze values
        n = 20
        retry = 40
        features = self.acquire_averaged_features(n, retry)

        # Swip columns in the arrays with gaze values
        flag_swip_cols = 0

        if flag_swip_cols:
            cr_array = features["cr_position_array"]
            tmp = cr_array[:, 1].copy()
            cr_array[:, 1] = cr_array[:, 0]
            cr_array[:, 0] = tmp
            pupil_array = features["pupil_position_array"]
            tmp = pupil_array[:, 1].copy()
            pupil_array[:, 1] = pupil_array[:, 0]
            pupil_array[:, 0] = tmp

        else:
            cr_array = features["cr_position_array"]
            pupil_array = features["pupil_position_array"]

        # Convert pixel arrays to degree
        elevation, azimuth = self.transform(pupil_array, cr_array)

        print "#########  Set of pupil measurements (deg): ##########\n"
        print "Azimuth =\n", azimuth
        print "Elevation =\n", elevation

        print "#########  Set of top CR measurements (pix): ##########\n"
        print "x =\n", cr_array[:, 0]
        print "y =\n", cr_array[:, 1]

        return mean(azimuth), mean(elevation), std(azimuth), std(elevation)

    def acquire_averaged_features(self, n, retry=200):

        pupil_radius = array([])
        cr_radius = array([])
        pupil_position = zeros((1, 2))      # this first row is just for initialization (it should be removed once the array is filled)
        cr_position = zeros((1, 2))
        n_count = 0
        n_attempt = 0
        frame_list = []

        # Create and run a local ROI instance
        roi = ROISelect(self.camera_type, add_axes=True)
        roi.findROI()
        ROI, roi_diff, pupil, cr = roi.getData()

        # Set ROI for camera
        self.camera.roi = ROI

        # Start camera
        self.camera.start_cap()

        # Set guess for feature finder
        if pupil != []:
            self.pos_guess["pupil_position"] = array(pupil[0])

        if cr != []:
            self.pos_guess["cr_position"] = array(cr[0])

        # Acquire frames from camera
        while n_count < n and n_attempt < retry:

            if self.camera_type == 'Point_Grey':
                # Changed for use with OpenCV and grasshopper cam - MM
                # Gets the full frame
                im = self.camera.dequeue(send=1)

                # Only want ROI for feature finding
                frame = im[ROI[0][1]:ROI[1][1], ROI[0][0]:ROI[1][0]]

            elif self.camera_type != 'Point_Grey':
                im = self.camera.readFrame(send=1)

                # Only want ROI for feature finding
                frame = im[ROI[0][1]:ROI[1][1], ROI[0][0]:ROI[1][0]]

            if frame is None:
                n_attempt += 1
            else:
                # Apply image preprocessing to frame and add to stack
                frame = self.adjust_image(frame, 4, 3, 20)
                frame_list.append(frame.copy())
                n_count += 1

        self.feature_finder.analyze_image(frame_list, self.pos_guess)
        features = self.feature_finder.get_result()

        # Disconnect camera (only of PTGrey cameras. webcams can be connected arbitrarily)
        if self.camera_type == 'Point_Grey':
            self.camera.c.stop_capture()

        # Testing on the key 'pupil_position' is enough to guarantee that all other relevant parameters exist
        if features is not None and features['pupil_position'] is not None:
            pupil_radius = features['pupil_radius']
            cr_radius = features['cr_radius']
            pupil_position = features['pupil_position']
            cr_position = features['cr_position']

            if not self.quiet:
                print "\n"
                print "LAST pupil radius = ", features['pupil_radius']
                print "LAST cr radius = ", features['cr_radius']
                print "LAST pupil position = ", features['pupil_position']
                print "LAST cr position = ", features['cr_position']
                print "\n"

            # Compensate for ROI selection so centering with reference to entire frame is valid
            # This is only used for calibrating
            features['pupil_position'] = [pupil_position[i] + roi_diff[i] for i in xrange(len(roi_diff))]
            features['cr_position'] = [cr_position[i] + roi_diff[i] for i in xrange(len(roi_diff))]

            return features
        # ######### End of Davide's implementation #########

    def adjust_image(self, image, gamma, contrast, brightness):
        # adjust contrast and brightness
        image = image * contrast + brightness

        # Set thresholds
        image[image < 0] = 1
        image[image > 255] = 255
        image = image.astype('uint8')

        # adjust gamma
        image = self.adjust_gamma(image, gamma)

        # Equalize histogram across the image to get pupil enhancement
        image = cv2.equalizeHist(image)

        # Smooth image
        image = cv2.blur(image, (5, 5))

        return image

    def adjust_gamma(self, image, gamma):
        # build a lookup table mapping the pixel values [0, 255] to
        # their adjusted gamma values
        invGamma = 1.0 / gamma
        table = array([((i / 255.0) ** invGamma) * 255 for i in arange(0, 256)]).astype("uint8")

        # apply gamma correction using the lookup table
        return cv2.LUT(image, table)

    def calibrate(self):
        """Calibrate the eye tracker manipulating stages and leds as needed.

            Following this call, the transform method will convert image coordinates
            to degrees"""
        
        print "Manual calibration initiated. This will take a few minutes. \n"
        print "Enter starting positions of stage axes."
        self.x_position = float(raw_input("Enter the displacement value of the x_axis (horizontal) stage: "))
        self.y_position = float(raw_input("Enter the displacement value of the y_axis (rostral-caudal) stage: "))
        self.z_position = float(raw_input("Enter the displacement value of the z_axis (vertical) stage: "))
        
        # calibrate the eye tracker in four steps
        print "\nCENTER HORIZONTAL"
        self.center_horizontal()
        self.x_position = input("Enter the displacement value of the x_axis (horizontal) stage: ")

        print "\nCENTER VERTICAL"
        self.center_vertical()
        self.z_position = input("Enter the displacement value of the z_axis (vertical) stage: ")

        print "\nCENTER DEPTH"
        self.center_depth_faster_manual()
        
        # This section is unnecessary because we can just turn the camera by hand
        raw_input("Rotate torch so pupil and LED reflection are vertically aligned. Press enter to continue.")
        #print "ALIGN PUPIL AND CR"
        #self.align_pupil_and_CR()

        print "\nFIND PUPIL RADIUS"
        self.find_pupil_radius_manual()
        print "d = ", self.d
        print "Rp[mm] = ", self.Rp_mm
        
        
        print "\n FINAL CHECK"
        print "x stage position [mm]:", self.x_position 
        print "y stage position [mm]:", self.y_position 
        print "z stage position [mm]:", self.z_position 
        raw_input("Ensure three-axis stage is set to these positions. \nCenter camera on rail "
                  "and set rotation to zero degrees. \nPress enter to save parameters.\n")

    def transform(self, pupil_coordinates, cr_coordinates):
        """Convert image (pixel) coordinates to degrees of visual angle"""

        transform_vector = True
        #
        # which_led = self.no_led
        #
        # # check which LED is on
        # if self.top_led:
        #     which_led = self.top_led
        #
        # if self.side_led:
        #     which_led = self.side_led
        #
        # # check if both LEDs are on.
        # if self.side_led and self.top_led:
        #     which_led = self.both_leds
        #     cr_coordinates = None       # these are junk if both are on

        # establish the calibration status, this will be forwarded
        # on so that a decision can be made about how to treat this data
        # calibration_status = self.uncalibrated
        # if cr_coordinates is None and not self.calibrated:
        #     calibration_status = self.pupil_only_uncalibrated
        # elif cr_coordinates is None and self.calibrated:
        #     calibration_status = self.pupil_only
        # elif self.calibrated:
        #     calibration_status = self.full_calibration
        # else:
        #     calibration_status = self.uncalibrated

        if not self.calibration_status:
            return pupil_coordinates[0], pupil_coordinates[1], self.calibration_status

        if pupil_coordinates.ndim == 1:
            transform_vector = False
            pupil_coordinates = array([pupil_coordinates])
            cr_coordinates = array([cr_coordinates])

        y_equator = self.y_equator + (cr_coordinates[:, self.y_image_axis] - self.y_topCR_ref)

        if self.Rp is None:
            Rp = self.default_Rp
        else:
            Rp = self.Rp

        y_displacement = pupil_coordinates[:, self.y_image_axis] - y_equator

        elevation = -arcsin(y_displacement / Rp) * 180/pi
        azimuth = arcsin((pupil_coordinates[:, self.x_image_axis] - cr_coordinates[:, self.x_image_axis]) / sqrt(Rp**2 - y_displacement**2)) * 180/pi

        if transform_vector:
            return elevation, azimuth

        return elevation[0], azimuth[0]

    def center_horizontal(self):
        """Horizontally align the camera with the eye"""
        print "Calibrator: centering horizontal"
        self.center_axis_manual(self.x_stage_axis)

        # Save the position of the CR spot with the light on the top: this is the displacement
        # y coordinate of the equator when running with the top LED on
        if self.top_led in self.default_cr_positions:
            self.y_topCR_ref = self.default_cr_positions[self.top_led][self.y_image_axis]

    def center_vertical(self):
        """Vertically align the camera with the eye"""
        print "Calibrator: centering vertical"
        self.center_axis_manual(self.y_stage_axis)

        # Save the position of the CR spot with the light on the side: this is the y coordinate of the equator
        if self.side_led in self.default_cr_positions:
            self.y_equator = self.default_cr_positions[self.side_led][self.y_image_axis]

    def center_axis_manual(self, stage_axis):
        """Align the camera with the eye along the specified axis"""
        
        Dx = self.Dx   # a quantum of stage displacement in millimeters
        
        # 1. Turn on the {top|side} LED, turn off the {side|top} LED
        if stage_axis == 'x axis':
            chosen_led = self.top_led
            other_led = self.side_led
            im_axis = self.x_image_axis
            stage_direction = self.x_stage_direction
            move_direction = self.horizontal_dirs
            raw_input("Turn on top LED. Press enter to continue.")
            raw_input("Turn off side LED. Press enter to continue.")            
        else:
            chosen_led = self.side_led
            other_led = self.top_led
            im_axis = self.y_image_axis
            stage_direction = self.y_stage_direction
            move_direction = self.vertical_dirs
            raw_input("Turn on side LED. Press enter to continue.")
            raw_input("Turn off top LED. Press enter to continue.") 

        # 2. Get the first CR and Pupil Positions
        # acquire, analyze
        print "Acquiring images and finding initial data"
        features = self.acquire_averaged_features(self.n_calibration_samples)

        original_cr = features["cr_position"]
        original_pupil = features["pupil_position"]

        if self.center_camera_frame is not None:
            print "ALIGN TO THE CENTER OF CAMERA FRAME"
            im_center = self.center_camera_frame
        else:
            print "ALIGN TO THE CENTER OF ACQUIRED IMAGE"
            im_shape = [self.camera.height, self.camera.width]
            im_center = array(im_shape) / 2.

        """"Maybe put a function displaying the last image up here"""

        print("ORIGINAL CR POSITION = %.1f, %.1f" % tuple(original_cr))
        print("ORIGINAL PUPIL POSITION = %.1f, %.1f" % tuple(original_pupil))
        print("IMAGE CENTER = %.1f, %.1f \n" % tuple(im_center))

        # 3. Move the stage towards the center in the {X|Y} direction
        Dx_sign = 1.
        if original_cr[im_axis] < im_center[im_axis]:
            Dx_sign = -1.
        Dx_actual = stage_direction * Dx_sign * Dx  
        
        if Dx_actual < 0:
            move = move_direction[0]
        else:
            move = move_direction[1]
           
        raw_input("Move camera " + str(Dx) + "mm " + move + ". Press enter to continue.")

        # 4. Get the CR and Pupil Positions again
        features = self.acquire_averaged_features(self.n_calibration_samples)

        cr = features["cr_position"]
        pupil = features["pupil_position"]

        print("CR POSITION = %.1f, %.1f" % tuple(cr))
        print("PUPIL POSITION = %.1f, %.1f" % tuple(pupil))

        # 5. Compute the slope (pixels / mm)
        slope = (cr[im_axis] - original_cr[im_axis]) / Dx_actual
        print("Slope = %0.3f" % slope)

        self.pixels_per_mm = abs(slope)
        print "Estimate of image resolution: %.3f pixels/mm \n" % self.pixels_per_mm

        # 6. Move to center in the {X|Y} direction
        raw_input("Align LED reflection with the " + self.axis_dirs[im_axis] + " axis. Press enter to continue.")
        
        # Check if CR within tolerances
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr = features["cr_position"]
        pupil = features["pupil_position"]        
        
        count = 0

        # Check to see if CR position is within tolerance of axis
        if abs(cr[im_axis] - im_center[im_axis]) > self.cr_tolerances:

            print("Alignment outside tolerances!")
            tolerance = raw_input("Further adjustment necessary. Align LED reflection with the " +
                                  self.axis_dirs[im_axis] + " axis. Press enter to continue or Q to skip.")

            if tolerance == 'q' or tolerance == 'Q':
                pass

            elif tolerance == '':
                while count < 3:
                    features = self.acquire_averaged_features(self.n_calibration_samples)
                    cr = features["cr_position"]
                    pupil = features["pupil_position"]

                    # Check if requirement is met
                    if abs(cr[im_axis] - im_center[im_axis]) > self.cr_tolerances:
                        raw_input("Further adjustment necessary. Align LED reflection with the " +
                                  self.axis_dirs[im_axis] + " axis. Press enter to continue.")
                    else:
                        break

                    count += 1

        if abs(cr[im_axis] - im_center[im_axis]) > self.cr_tolerances:
            print("Centering requirements not met. Continuing calibration. \n")
        else:
            print("Alignment successful! \n")
            
        # 7. (Optional) Report the CR and Pupil Positions, as well as the stage position
        #features = self.acquire_averaged_features(self.n_calibration_samples)  
        print("FINAL CR POSITION =%.1f, %.1f" % tuple(features["cr_position"]))
        print("FINAL PUPIL POSITION = %.1f, %.1f \n" % tuple(features["pupil_position"]))            

        self.default_cr_positions[chosen_led] = features["cr_position"]

        return

    def jogged_cr_difference(self, d, rs, axis):

        cr_pos = []
        for i in range(0, 2):
            d_new, reversal_function = self.stages.composite_rotation_relative(d, rs[i])

            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos.append(features["cr_position"])
            reversal_function()

        print "########## in _jogged_cr_difference:"
        print "cr pos 1st =", cr_pos[0][axis], "cr pos 2nd =", cr_pos[1][axis]
        print "DIFFERENCE CRs =", cr_pos[0][axis] - cr_pos[1][axis]
        return cr_pos[0][axis] - cr_pos[1][axis]

    def jogged_pupil_cr_difference(self, d, r, axis):

        d_new, reversal_function = self.stages.composite_rotation_relative(d, r)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]
        reversal_function()

        print "########## in _jogged_pupil_cr_difference:"
        print "cr pos =", cr_pos[axis], "pupil pos =", pupil_pos[axis]
        print "DIFFERENCE CR - PUPIL =", cr_pos[axis] - pupil_pos[axis]
        return cr_pos[axis] - pupil_pos[axis]
        
    def center_depth_faster_manual(self):
        """" Fit a linear function to the depth vs. cr-displacement data to find the zero point in a hurry
        """
        """" Vary the radius of rotation of the camera, until the CR spot is stable in the image (i.e., it does not move when the camera rotates to
             the left or to the right).
        """

        print "Centering depth (manually)"
        # 1. Turn on the top LED, turn off the side LED
        raw_input("Turn on top LED. Press enter to continue.")
        raw_input("Turn off side LED. Press enter to continue.\n")             

        # 2. Sample some distances in the range self.d_guess +/- self.d_half_range
        n_points_to_sample = 4
        ds = linspace(self.d_guess - self.d_halfrange, self.d_guess + self.d_halfrange, n_points_to_sample)
        measured_cr_displacements_pos = []
        measured_cr_displacements_neg = []
        
        # set the "default" cr position
        features = self.acquire_averaged_features(self.n_calibration_samples)
        base_cr = features["cr_position"]        

        translation = []

        # Calculate x translation needed to achieve 15 degree pseudo-rotation about center of sphere using d_guess 
        # Assume the rig is positioned at some arbitrary zero point where the eye is centered        
        
        # initial absolute stage values
        x0 = float(raw_input("Enter current x position in mm: "))
        r0 = float(raw_input("Enter current stage rotation from zero (in degrees): "))        
        
        for d in ds:
            
            r_rel = float(self.jog_angle)               # angle of rotation we want to move
            d = float(d)                                # guess for distance to center of rotation
        
            # Compute target absolute stage values
            # This is a catch-all case for the situation where the camera is already at an angle and translated in x direction. 
            # This reduces to a simple tangent function when initial positions are at zero
            r_abs = r0 + r_rel
            x_abs = x0 - d * sin(r0 * math.pi / 180) + d * cos(r0 * math.pi / 180) * tan(r_abs * math.pi / 180)
        
            # Compute the new distance of the rotation center from the camera (following the current relative rotation)
            d_new = d * cos(r0 * math.pi / 180) / cos(r_abs * math.pi / 180)            
            
            # Add movements needed to list
            # If negative, this can be simply ignored
            translation.append(abs(x_abs))

        # make the movements and acquire image  
        raw_input("Rotate rig by -10 deg. Press enter to continue.")
        for movement in translation:
            raw_input("Move horizontal axis stage %.0f mm to the right from zero position. Press enter to continue." % movement)
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            measured_cr_displacements_pos.append(cr_pos[1])
            
            
        raw_input("Return rig to zero position on rail and rotate to +10 deg. Press enter to continue.")
        for movement in translation:
            raw_input("Move horizontal axis stage %.0f mm to the left from zero position. Press enter to continue." % movement)
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            measured_cr_displacements_neg.append(cr_pos[1])

        measured_cr_displacements = array(measured_cr_displacements_pos) - array(measured_cr_displacements_neg)

        # return to our original position
        
        raw_input("Return rig to starting position. Press enter to continue.")
        
        print "ds = ", ds
        print "cr_diffs = ", array(measured_cr_displacements)

        X = hstack((array([ds]).T, ones_like(array([ds]).T)))
        cr_diff_vector = array([measured_cr_displacements]).T

        params = dot(linalg.pinv(X), cr_diff_vector)
        self.d = double(-params[1] / params[0])

        print("=====================================")
        print("D (faster) = %f" % self.d)
        print("=====================================")        

    def align_pupil_and_CR(self):
        """ Vary the angle of rotation of the camera, until the CR and the pupil are vertically aligned.

            This is achieved with an adaptive search loop that stops when the difference
            between the x coordinate of the CR and pupil is smallenough or a maximum # of loops
            are executed.

            Side effects: camera will be moved so that the CR and pupil are on top of each other
        """

        # 1. Turn on the top LED, turn off the side LED

        # 2. Adaptively optimize (this actually moves the stages)
        range = [-20., 20.]
        objective_function = lambda x: abs(self.jogged_pupil_cr_difference(self.d, x, self.x_image_axis))
        r = scipy.optimize.fminbound(objective_function, range[0], range[1], (), self.cr_diff_threshold, 30)

        # 3. Move the camera in the final position with pupil and CR aligned
        self.d, reversal_function = self.stages.composite_rotation_relative(self.d, r)

        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]

        print("=====================================")
        print "Final CR position =", cr_pos
        print "Final Pupil position =", pupil_pos
        print("D = ", self.d)
        print("=====================================")

        return

    def find_pupil_radius(self):
        """
            Compute Rp, the distance from the center of the corneal curvature to the pupil

            This is accomplished by rotating the camera around the eye and measuring the image displacement
            of the stationary pupil

            Side effects: self.Rp is set to the compute Radius of the pupil's rotation about the center of
            the corneal curvature
        """

        # 1. Turn on the top LED, turn off the side LED

        # 1.b Take one measurement at the zero angle
        features = self.acquire_averaged_features(self.n_calibration_samples)
        pupil_pos_0 = features["pupil_position"]

        # 2. Take measurements of x displacement while moving camera
        #    This is sort of like "manually" rotating the eye, since, at this
        #    point in the calibration we are able to rotate the camera about the
        #    center of the eye
        n_angle_samples = 5
        x_displacements = []
        pup_radiuses = []
        rs = linspace(-self.jog_angle, self.jog_angle, n_angle_samples)

        # precompute the movements so that we can make them faster and in succession
        precomputed_motions = []
        true_distances = []
        for r in rs:
            motion_func, d_new = self.stages.precompute_composite_rotation_relative(self.d, r)
            precomputed_motions.append(motion_func)
            true_distances.append(d_new)
        return_motion = self.stages.precompute_return_motion()

        for i in range(0, len(precomputed_motions)):
            precomputed_motion = precomputed_motions[i]
            distance = true_distances[i]
            print "-----> distance =", distance

            # take one measurement
            precomputed_motion()
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            pupil_pos = features["pupil_position"]

            relative_magnification = distance / self.d
            #relative_magnification = 1.
            #relative_magnification = 1.012
            print "relative_magnification =", relative_magnification

            displacement = (cr_pos[self.x_image_axis] - pupil_pos[self.x_image_axis]) * relative_magnification
            x_displacements.append(displacement)
            pup_radiuses.append(features["pupil_radius"] / relative_magnification)

        return_motion()


        # 3. We now need to take a measurement to see how far off of the
        #    "equator" the pupil currently is.
        #    To do this, we'll turn on the "side" LED
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)

        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]

        y_displacement = pupil_pos[self.y_image_axis] - cr_pos[self.y_image_axis]

        # Save the position of the CR spot with the light on the side: this is the y coordinate of the equator
        self.y_equator = cr_pos[self.y_image_axis]


        # Now compute the Rp, based on the displacements
        self.Rp = self._compute_Rp(x_displacements, radians(rs), y_displacement)
        self.Rp_mm = self.Rp/self.pixels_per_mm


        print("=====================================")
        print("Rp = ", self.Rp)
        print("=====================================")

        # 4. Turn back on the top LED to prepare for eye tracking
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        # Save the final y value of the CR as a reference to measure how much y displacement we get during eye tracking
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        self.y_topCR_ref = cr_pos[self.y_image_axis]

        #pupil_radius = features["pupil_radius"]

        print pup_radiuses
        pupil_radius = mean(pup_radiuses)

        cornea_curvature_radius = sqrt( pupil_radius**2 + self.Rp**2 )
        print("================== EYE MEASUREMENTS IN PIXELS ===================")
        print("pupil size = ", pupil_radius)
        print("Rp = ", self.Rp)
        print("Cornea curvature radius = ", cornea_curvature_radius)
        print("=====================================")

        print("================== EYE MEASUREMENTS IN MM ===================")
        print("pupil size = ", pupil_radius/self.default_pixels_per_mm)                                                                         # Shitty hack, need to fix
        print("Rp = ", self.Rp/self.pixels_per_mm)
        print("Cornea curvature radius = ", cornea_curvature_radius/self.pixels_per_mm)
        print("=====================================")
        return
    
    def find_pupil_radius_manual(self):
        """
            Compute Rp, the distance from the center of the corneal curvature to the pupil

            This is accomplished by rotating the camera around the eye and measuring the image displacement
            of the stationary pupil

            Side effects: self.Rp is set to the compute Radius of the pupil's rotation about the center of
            the corneal curvature
        """

        # 1. Turn on the top LED, turn off the side LED
        raw_input("Turn on top LED. Press enter to continue.")
        raw_input("Turn off side LED. Press enter to continue.")  

        # 1.b Take one measurement at the zero angle
        features = self.acquire_averaged_features(self.n_calibration_samples)
        pupil_pos_0 = features["pupil_position"]

        # 2. Take measurements of x displacement while moving camera
        #    This is sort of like "manually" rotating the eye, since, at this
        #    point in the calibration we are able to rotate the camera about the
        #    center of the eye
        n_angle_samples = 5
        x_displacements = []
        pup_radiuses = []
        rs = linspace(-self.jog_angle, self.jog_angle, n_angle_samples)

        # precompute the movements so that we can make them faster and in succession
        true_distances = []
        translation = []
        
        # initial absolute stage values
        x0 = float(raw_input("Enter current x position in mm: "))
        r0 = float(raw_input("Enter current stage rotation from zero (in degrees): "))      
        
        for r in rs:
            r_rel = float(r)               # angle of rotation we want to move
            d = float(self.d)              # known distance to center of rotation
        
            # Compute target absolute stage values
            # This is a catch-all case for the situation where the camera is already at an angle and translated in x direction. 
            # This reduces to a simple tangent function when initial positions are at zero
            r_abs = r0 + r_rel
            x_abs = x0 - d * sin(r0 * math.pi / 180) + d * cos(r0 * math.pi / 180) * tan(r_abs * math.pi / 180)
        
            # Compute the new distance of the rotation center from the camera (following the current relative rotation)
            d_new = d * cos(r0 * math.pi / 180) / cos(r_abs * math.pi / 180)            
            
            # Add movements needed to list
            translation.append(x_abs)
            true_distances.append(d_new)

        for i in range(0, len(translation)):
            x_move = translation[i]
            rotation = rs[i]
            raw_input("Move horizontal axis stage %.0f mm from zero position and rotate %0.f degrees. Press enter to continue." % (x_move, rotation))
            distance = true_distances[i] 
            print "-----> distance =", distance

            # take one measurement    
            features = self.acquire_averaged_features(self.n_calibration_samples)
            cr_pos = features["cr_position"]
            pupil_pos = features["pupil_position"]

            relative_magnification = distance / self.d
            print "relative_magnification =", relative_magnification

            displacement = (cr_pos[self.x_image_axis] - pupil_pos[self.x_image_axis]) * relative_magnification
            x_displacements.append(displacement)
            pup_radiuses.append(features["pupil_radius"] / relative_magnification)

        # 3. We now need to take a measurement to see how far off of the
        #    "equator" the pupil currently is.
        #    To do this, we'll turn on the "side" LED
        raw_input("Turn off top LED. Press enter to continue.")
        raw_input("Turn on side LED. Press enter to continue.")  

        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        pupil_pos = features["pupil_position"]

        y_displacement = pupil_pos[self.y_image_axis] - cr_pos[self.y_image_axis]

        # Save the position of the CR spot with the light on the side: this is the y coordinate of the equator
        self.y_equator = cr_pos[self.y_image_axis]

        # Now compute the Rp, based on the displacements
        self.Rp = self._compute_Rp(x_displacements, radians(rs), y_displacement)
        self.Rp_mm = self.Rp/self.pixels_per_mm


        print("=====================================")
        print("Rp = ", self.Rp)
        print("=====================================")

        # 4. Turn back on the top LED to prepare for eye tracking
        print "Prepare for eye tracking."
        raw_input("Turn on top LED. Press enter to continue.")
        raw_input("Turn off side LED. Press enter to continue.")  

        
        # Save the final y value of the CR as a reference to measure how much y displacement we get during eye tracking
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos = features["cr_position"]
        self.y_topCR_ref = cr_pos[self.y_image_axis]

        #pupil_radius = features["pupil_radius"]

        print pup_radiuses
        pupil_radius = mean(pup_radiuses)

        cornea_curvature_radius = sqrt(pupil_radius**2 + self.Rp**2)
        print("================== EYE MEASUREMENTS IN PIXELS ===================")
        print("pupil size = ", pupil_radius)
        print("Rp = ", self.Rp)
        print("Cornea curvature radius = ", cornea_curvature_radius)
        print("=====================================")

        print("================== EYE MEASUREMENTS IN MM ===================")
        print("pupil size = ", pupil_radius/self.pixels_per_mm)                          # Shitty hack, need to fix
        print("Rp = ", self.Rp/self.pixels_per_mm)
        print("Cornea curvature radius = ", cornea_curvature_radius/self.pixels_per_mm)
        print("=====================================")
        return        

    def _compute_Rp(self, x_displacements, angle_displacements, y_displacement):
        # compute "Rp_prime", which is the "in-plane" Rp, which doesn't
        # take into account that the pupil may not currently be on the
        # eye's "equator"
        p0 = (6.0, radians(0))
        leastsq_results = scipy.optimize.leastsq(self.residuals_sine, p0, (x_displacements, angle_displacements))
        p = leastsq_results[0]
        Rp_prime = p[0]
        angle_offset = p[1]

        print("Rp_prime = %g" % Rp_prime)
        print("Angle Offset = %g" % angle_offset)

        # now correct Rp taking this vertical offset into account
        return sqrt( Rp_prime**2 + y_displacement**2 );

    def residuals_sine(self, p, y, x):
        A, theta = p
        err = y - A*sin(x+theta)
        return err

    def find_center_camera_frame(self):

        zoom_step = 60

        # 1) Measure the CR position (top and side) at the current zoom level

        # Turn on the top LED and take one measurement
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_top = features["cr_position"]
        # Turn on the side LED and take another measurement
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_side = features["cr_position"]

        print "INITIAL ZOOM"
        print "CR top =", cr_pos_top
        print "CR side =", cr_pos_side

        # 2) Change the focus and measure again the CR position (top and side)
        self.focus_and_zoom.zoom_relative(zoom_step)
        # Turn on the top LED and take one measurement
        self.leds.turn_on(self.top_led)
        self.leds.turn_off(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_top_zoom = features["cr_position"]
        # Turn on the side LED and take another measurement
        self.leds.turn_off(self.top_led)
        self.leds.turn_on(self.side_led)
        features = self.acquire_averaged_features(self.n_calibration_samples)
        cr_pos_side_zoom = features["cr_position"]

        print "FINAL ZOOM"
        print "CR top =", cr_pos_top_zoom
        print "CR side =", cr_pos_side_zoom

        # Find the straight lines through the pairs of top and side CR values
        m_top = (cr_pos_top_zoom[0] - cr_pos_top[0]) / (cr_pos_top_zoom[1] - cr_pos_top[1])
        p_top = cr_pos_top[0] - m_top * cr_pos_top[1]
        m_side = (cr_pos_side_zoom[0] - cr_pos_side[0]) / (cr_pos_side_zoom[1] - cr_pos_side[1])
        p_side = cr_pos_side[0] - m_side * cr_pos_side[1]

        # Find the intersection of the lines
        x_cross = (p_side - p_top) / (m_top - m_side)
        y_cross = p_top + m_top * x_cross

        self.center_camera_frame = array( [y_cross, x_cross] )
        print "CENTER OF THE CAMERA FRAME =", self.center_camera_frame

    def fit_pupil_radius_size(self):
        """
            Repeat the computation of Rp for different intensities of the visible light (i.e., puil sizes)

            A linear fit between measured Rps and pupil sizes is performed to obtain the relationship
            between these variables.
        """

        pass




# @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@  class: CompensateLensDistorsion  @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
class CompensateLensDistorsion:

    # ==================================== method: __init__ ========================================
    def __init__( self ):

        #-- Focal length:
        self.fc = matrix( [ 6599.034515358368481, 7284.138084589575556 ] ).transpose();

        #-- Principal point:
        self.cc = matrix( [ 329.000000000000000, 246.500000000000000 ] ).transpose();

        #-- Skew coefficient:
        self.alpha_c = 0.000000000000000;

        #-- Distortion coefficients:
        self.kc = matrix( [ -15.229429242857810, 3684.210775878747427, -0.244109807331619, 0.153912004435507, 0.000000000000000 ] ).transpose();

        self.quiet = True


    # ==================================== method: test ========================================
    def test( self, FileName ):

        im = Image.open(FileName)
        X, Y = meshgrid( arange(5,650,25), arange(5,490,25))
        X.shape = ( 1, X.shape[0]*X.shape[1])
        Y.shape = ( 1, Y.shape[0]*Y.shape[1])

        x_kk = vstack(  (X, Y) )
        print 'x_kk shape =', x_kk.shape

        # Recover normalized coordinates (use default calibration parameters)
        xn = self.normalize( x_kk, None )
        print 'xn shape =', xn.shape


        # Transform them into pixels
        x_pix = self.map_cameraframe2pix( xn )
        print 'x_pix shape =', x_pix.shape

        # Display result
        figure();
        imshow(im);
        hold('on')
        plot( x_kk[0,:], x_kk[1,:], 'xr')
        plot( x_pix[0,:], x_pix[1,:], 'og')


    # ==================================== method: normalize ========================================
    def normalize( self, x_kk, calib_params ):
        """
            Computes the normalized coordinates xn given the pixel coordinates x_kk
            and the intrinsic camera parameters fc, cc and kc.

            INPUT: x_kk: Feature locations on the images
                   fc: Camera focal length
                   cc: Principal point coordinates
                   kc: Distortion coefficients
                   alpha_c: Skew coefficient

            OUTPUT: xn: Normalized feature locations on the image plane (a 2XN matrix)

            Important methods called within that program:

            comp_distortion_oulu: undistort pixel coordinates.
        """

        if calib_params is not None:
            if('alpha_c' not in calib_params or calib_params['alpha_c'] is None):
                self.alpha_c = 0
            if('kc' not in calib_params or calib_params['kc'] is None):
                self.kc = matrix([0,0,0,0,0]).transpose()
            if('cc' not in calib_params or calib_params['cc'] is None):
                self.cc = matrix([0,0]).transpose()
            if('cc' not in calib_params or calib_params['cc'] is None):
                self.fc = matrix([1,1]).transpose()

        # First: Subtract principal point, and divide by the focal length:
        x_distort = array( [ (x_kk[0,:] - self.cc[0,0])/self.fc[0,0], (x_kk[1,:] - self.cc[1,0])/self.fc[1,0] ] )

        # Second: undo skew
        x_distort[0,:] = x_distort[0,:] - self.alpha_c * x_distort[1,:]

        if linalg.norm(self.kc) is not 0:
            # Third: Compensate for lens distortion:
            xn = self.comp_distortion_oulu( x_distort, self.kc )
        else:
            xn = x_distort;

        return xn


    # ==================================== method: comp_distortion_oulu ========================================
    def comp_distortion_oulu( self, xd, k ):
        """
            Compensates for radial and tangential distortion. Model From Oulu university.
            For more informatino about the distortion model, check the forward projection mapping function:
            project_points.m

            INPUT: xd: distorted (normalized) point coordinates in the image plane (2xN matrix)
                   k: Distortion coefficients (radial and tangential) (4x1 vector)

            OUTPUT: x: undistorted (normalized) point coordinates in the image plane (2xN matrix)

            Method: Iterative method for compensation.

            NOTE: This compensation has to be done after the subtraction
                  of the principal point, and division by the focal length.
        """

        # k has has only one element
        if k.shape[0] == 1:

            radius_2 = sum(xd**2,0)
            radial_distortion = 1 + ones((2,1)) * (k * radius_2)
            radius_2_comp = (xd[0,:]**2 + xd[1,:]**2) / radial_distortion[0,:]
            radial_distortion = 1 + ones((2,1)) * (k2 * radius_2_comp)
            x = xd / radial_distortion

        # k has more than one element
        else:

            k1 = k[0,0];
            k2 = k[1,0];
            k3 = k[4,0];
            p1 = k[2,0];
            p2 = k[3,0];

            # initial guess
            x = xd;

            for kk in arange(0,20):
                r_2 = sum(x**2,0)
                k_radial =  1 + k1 * r_2 + k2 * r_2**2 + k3 * r_2**3
                delta_x = array( [ 2*p1*x[0,:]*x[1,:] + p2*(r_2 + 2*x[0,:]**2), p1 * (r_2 + 2*x[1,:]**2)+2*p2*x[0,:]*x[1,:] ] )
                x = (xd - delta_x) / (ones((2,1))*k_radial)

        return x


    # ==================================== method: map_cameraframe2pix ========================================
    def map_cameraframe2pix( self, xn ):
        """
            Map back from camera frame normalized coordinates to pixels
        """

        D = array( [ [self.fc[0,0], 0], [0, self.fc[1,0]] ] )
        Uo = array( [ [self.cc[0,0], 0], [0, self.cc[1,0]] ] )

        if not self.quiet:
            print 'D shape =', D.shape
            print 'xn shape =', xn.shape
            print 'D*xn shape =', dot(D,xn).shape
            print 'Uo*ones shape =', dot(Uo, ones( (2,xn.shape[1]) ) ).shape

        x_pix = dot(D,xn) + dot( Uo, ones( (2,xn.shape[1]) ) )

        if not self.quiet:
            print 'x_pix shape =', x_pix.shape

        return x_pix


    # ==================================== method: fully_compensate ========================================
    def fully_compensate( self, x_kk, calib_params ):
        """
            Do the full compensation of lens distorsion:
            x_kk -> xn -> x_pix
        """

        # Recover normalized coordinates (x_kk -> xn)
        xn = self.normalize( x_kk, None )

        # Transform them into pixels (xn -> x_pix)
        x_pix = self.map_cameraframe2pix( xn )

        return x_pix



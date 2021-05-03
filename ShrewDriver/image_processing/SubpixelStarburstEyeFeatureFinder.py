#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Dave's StarburstEyeFeatureFinder.py
#  EyeTracker
#
#  Created by David Cox on 3/9/09.
#  Copyright (c) 2009 Harvard University. All rights reserved.

# Last modified by Matthew McCann 02/16/2017

# In general, this code is the same as the original from the Cox lab. The only
# updates have been to calculate the Sobel filter using OpenCV, to add an
# averaging step in the Sobel filtered images, and to change the thresholding
# search criteria.

from __future__ import division
import matplotlib.pyplot as plt
import scipy.optimize
from numpy import *
import cv2


class SubpixelStarburstEyeFeatureFinder:

    def __init__(self, **kwargs):
        self.parameters_updated = False

        # A cached sobel filtered image to speed up initial computations
        self.shortcut_sobel = kwargs.get('shortcut_sobel', None)

        # following values in pixels
        self.cr_ray_length = kwargs.get('cr_ray_length', 6)
        self.pupil_ray_length = kwargs.get('pupil_ray_length', 45)
        self.cr_min_radius = kwargs.get('cr_min_radius', 1)
        self.pupil_min_radius = kwargs.get('pupil_min_radius', 10)

        # how many rays to shoot in the CR
        self.cr_n_rays = kwargs.get('cr_n_rays', 10)

        # how many rays to shoot in the pupil
        self.pupil_n_rays = kwargs.get('pupil_n_rays', 25)

        # how many pixels per sample along the ray
        self.cr_ray_sample_spacing = kwargs.get('cr_ray_sample_spacing', 0.5)
        self.pupil_ray_sample_spacing = kwargs.get('pupil_ray_sample_spacing', 1)

        # Set thresholds for edge detection
        self.cr_threshold = kwargs.get('cr_threshold', 100)
        self.pupil_threshold = kwargs.get('pupil_threshold', 40)

        self.ray_sampling_method = kwargs.get('ray_sampling_method', 'interp')

        self.fitting_algorithm = kwargs.get('fitting_algorithm', 'ellipse_least_squares')

        self.pupil_rays = None
        self.cr_rays = None

        self.x_axis = 0
        self.y_axis = 1
        self.ds_factor = 1
        self.target_kpixels = 40  # 8.0

        # rebuild parameters and cached constructs based on the current parameter settings
        self.update_parameters()

    def update_parameters(self):
        """ Reconstruct internal representations in response to new parameters
        being set. Recache rays, set method pointers, and clear storage for
        returned starburst parameters
        """

        if self.ray_sampling_method == 'interp':
            self._get_image_values = self._get_image_values_interp_faster
        else:
            self._get_image_values = self._get_image_values_nearest

        if self.fitting_algorithm == 'circle_least_squares':
            self._fit_points = self._fit_circle_to_points_lstsq
        elif self.fitting_algorithm == 'circle_least_squares_ransac':
            self._fit_points = self._fit_circle_to_points_lstsq_ransac
        elif self.fitting_algorithm == 'ellipse_least_squares':
            self._fit_points = self._fit_ellipse_to_points
        else:
            self._fit_points = self._fit_mean_to_points

        # how many samples per ray
        self.cr_ray_sampling = arange(0, self.cr_ray_length, self.cr_ray_sample_spacing)
        self.cr_ray_sampling = self.cr_ray_sampling[1:]  # don't need the zero sample
        self.cr_min_radius_ray_index = round(self.cr_min_radius / self.cr_ray_sample_spacing)

        self.pupil_ray_sampling = arange(0, self.pupil_ray_length, self.pupil_ray_sample_spacing)
        self.pupil_ray_sampling = self.pupil_ray_sampling[1:]  # don't need the zero sample
        self.pupil_min_radius_ray_index = round(self.pupil_min_radius / self.pupil_ray_sample_spacing)

        # ray BY ray samples BY x/y
        self.cr_rays = zeros((self.cr_n_rays, len(self.cr_ray_sampling), 2))
        self.pupil_rays = zeros((self.pupil_n_rays, len(self.pupil_ray_sampling), 2))

        # Choose ray angles in the range [0, 2pi)
        self.cr_ray_angles = linspace(0, 2 * pi, self.cr_n_rays + 1)
        self.cr_ray_angles = self.cr_ray_angles[0:-1]

        self.pupil_ray_angles = linspace(0, 2 * pi, self.pupil_n_rays + 1)
        self.pupil_ray_angles = self.pupil_ray_angles[0:-1]

        for r in range(0, self.cr_n_rays):
            ray_angle = self.cr_ray_angles[r]

            self.cr_rays[r, :, self.x_axis] = self.cr_ray_sampling * cos(ray_angle)
            self.cr_rays[r, :, self.y_axis] = self.cr_ray_sampling * sin(ray_angle)

        for r in range(0, self.pupil_n_rays):
            ray_angle = self.pupil_ray_angles[r]

            self.pupil_rays[r, :, self.x_axis] = self.pupil_ray_sampling * cos(ray_angle)
            self.pupil_rays[r, :, self.y_axis] = self.pupil_ray_sampling * sin(ray_angle)

        self.cr_boundary_points = None
        self.pupil_boundary_points = None
        self.cr_ray_starts = None
        self.cr_ray_ends = None
        self.pupil_ray_starts = None
        self.pupil_ray_ends = None
        self.parameters_updated = True

    def analyze_image(self, image_list, guess, **kwargs):
        """ Begin processing an image to find features

        Args:
            image_list: [list] list of numpy arrays of the images to be processed
            guess: [dict] guess for pupil and CR centers

        Returns: features
        """

        # This is no longer used. It used to be for speeding up some computations
        # with inline C++ code, but that's a giant pain in the ass on Windows,
        # so I changed things to use OpenCV instead.
        use_weave = kwargs.get('weave', 0)

        # Clear the result
        ds_image = []
        self.result = None

        # Use the first image as a representative example
        image = image_list[0]

        # Down sample image for speed
        im_pixels = image.shape[0] * image.shape[1]
        self.ds_factor = int(sqrt(im_pixels / int(self.target_kpixels * 1000)))

        if self.ds_factor <= 0:
            self.ds_factor = 1
        im_array = image[::self.ds_factor, ::self.ds_factor]

        # Apply down sampling to all images in image list
        ds_image = [item[::self.ds_factor, ::self.ds_factor] for item in image_list]

        # Assign some basic features for the frame
        features = {}

        if guess is not None and 'frame_number' in guess:
            features['frame_number'] = guess['frame_number']

        if guess is not None and 'timestamp' in guess:
            features['timestamp'] = guess['timestamp']

        if guess is not None and 'restrict_top' in guess:
            features['restrict_top'] = guess['restrict_top']
            features['restrict_bottom'] = guess['restrict_bottom']
            features['restrict_left'] = guess['restrict_left']
            features['restrict_right'] = guess['restrict_right']

        # This is the starting seed-point from which we will start
        # If no guess is provided, pick the image center as the guess
        # MM 11/1/16
        if guess is not None and 'pupil_position' in guess:
            pupil_guess = [item / self.ds_factor for item in guess['pupil_position']]
        else:
            pupil_guess = [im_array.shape[self.y_axis] / 2, im_array.shape[self.x_axis] / 2]

        if guess is not None and 'cr_position' in guess:
            cr_guess = [item / self.ds_factor for item in guess['cr_position']]
        else:
            cr_guess = [im_array.shape[self.y_axis] / 2, im_array.shape[self.x_axis] / 2]

        if guess is not None and 'cached_sobel' in guess:
            self.shortcut_sobel = guess['cached_sobel']

        # compute the image gradient
        if self.shortcut_sobel is None:
            image_grad_mag = zeros_like(ds_image[0], dtype=uint8)

            for im in ds_image:
                image_grad_mag1, _, _ = self.sobel_cv(im)
                # take average of sobel transforms  MM 12/15/2016
                image_grad_mag += (image_grad_mag1 // len(ds_image))

        else:
            image_grad_mag = self.shortcut_sobel

        # Do the heavy lifting
        if use_weave:
            # This is no longer used
            cr_boundaries = self._find_ray_boundaries_woven(image_grad_mag,
                                                            cr_guess, self.cr_rays,
                                                            self.cr_min_radius_ray_index,
                                                            self.cr_threshold)
        else:
            cr_boundaries = self._find_ray_boundaries(
                image_grad_mag, 
                cr_guess,
                self.cr_rays, 
                self.cr_min_radius_ray_index,
                self.cr_threshold,
                ray_type='cr'
                )

        # Find the position and radius of the CR
        cr_position, cr_radius, cr_err, _, _ = self._fit_points(cr_boundaries)

        # do a two-stage starburst fit for the pupil
        # stage 1, rough cut
        pupil_boundaries = self._find_ray_boundaries(
            image_grad_mag,
            pupil_guess,
            self.pupil_rays,
            self.pupil_min_radius_ray_index,
            self.pupil_threshold,
            secondary_thresh=self.cr_threshold,
            exclusion_center=array(cr_position),
            exclusion_radius=int(2 * cr_radius),
            ray_type='pupil'
            )

        pupil_position, pupil_radius, pupil_err, _, _ = self._fit_points(pupil_boundaries)
        if pupil_position.any == -1 or pupil_radius == 0.0:
            pupil_position = pupil_guess
            pupil_radius = self.pupil_min_radius_ray_index

        # stage 2: refine
        minimum_pupil_guess = round(0.5 * pupil_radius / self.pupil_ray_sample_spacing)

        pupil_boundaries = self._find_ray_boundaries(
            image_grad_mag,
            pupil_position,
            self.pupil_rays,
            minimum_pupil_guess,
            self.pupil_threshold,
            secondary_thresh=self.cr_threshold,
            exclusion_center=array(cr_position),
            exclusion_radius=int(2 * cr_radius),
            ray_type='pupil'
            )

        pupil_position, pupil_radius, pupil_err, pupil_orientation, pupil_short_axis = self._fit_points(pupil_boundaries)

        # Compensate for down sampling in boundary lists
        cr_bound = [item * self.ds_factor for item in cr_boundaries]
        pupil_bound = [item * self.ds_factor for item in pupil_boundaries]

        # Pack up the results
        # Note that all position results follow the [rows, columns] convention.
        # This means the formatting in Cartesian coordinates is [Y, X]
        try:
            features['cr_position'] = cr_position * self.ds_factor
            features['pupil_position'] = pupil_position * self.ds_factor
            features['cr_radius'] = cr_radius * self.ds_factor
            features['pupil_radius'] = pupil_radius * self.ds_factor
            features['pupil_short_axis'] = pupil_short_axis * self.ds_factor
            features['pupil_orientation'] = pupil_orientation
            if guess is not None:
                features['transform'] = guess.get('transform', None)

            starburst = {}
            starburst['cr_boundary'] = cr_bound
            starburst['pupil_boundary'] = pupil_bound
            starburst['cr_rays_start'] = self.cr_rays[:, 0, :] + cr_guess * self.ds_factor
            starburst['cr_rays_end'] = self.cr_rays[:, -1, :] + cr_guess * self.ds_factor
            starburst['pupil_rays_start'] = self.pupil_rays[:, 0, :] + pupil_guess * self.ds_factor
            starburst['pupil_rays_end'] = self.pupil_rays[:, -1, :] + pupil_guess * self.ds_factor
            starburst['cr_err'] = cr_err * self.ds_factor
            starburst['pupil_err'] = pupil_err * self.ds_factor
            features['starburst'] = starburst

        except Exception, e:
            print 'Error packing up results of image analysis'
            print e.message
            # formatted = formatted_exception()
            # print formatted[0], ': '
            # for f in formatted[2]:
            #     print f
            # raise

        self.result = features

    def sobel_cv(self, image):         # <-------      Modified by MM 2/16/2017
        """
        Uses OpenCV to compute the Sobel filter of an image

        Args:
            image: [np array] array containing an image

        Returns: [tuple] magnitude, x-direction, and y-direction of the
        Sobel filtered image with a 5px kernel Gaussian blur
        """
        sobel_c = array([-1, 0, 1])
        sobel_r = array([1, 2, 1])

        imgx = cv2.sepFilter2D(image, cv2.CV_64F, sobel_c, sobel_r, borderType=cv2.BORDER_DEFAULT)
        imgy = cv2.sepFilter2D(image, cv2.CV_64F, sobel_r, sobel_c, borderType=cv2.BORDER_DEFAULT)

        mag = sqrt(imgx ** 2 + imgy ** 2)
        mag = cv2.blur(mag, (5, 5))

        return mag.astype(uint8), imgx.astype(uint8), imgy.astype(uint8)

    def get_result(self):
        """ Get the result of a previous call to analyze_image.
            This call is separate from analyze_image so that analysis
            can be done asyncronously on multiple processors/cores
        """
        return self.result

    def _find_ray_boundaries(self, im, seed_point, zero_referenced_rays,
                             cutoff_index, threshold, **kwargs):
        """ Find where a set of rays crosses a threshold in an image

            Args:
            im: An image (usually a gradient magnitude image) in which crossing
                will be found
            seed_point: the origin from which rays will be projected
            zero_referenced_rays: the set of rays (starting at zero) to sample.
                                  nrays x ray_sampling x image_dimension
            cutoff_index: the index along zero_referenced_rays below which we
                          are sure that we are still within the feature. Used
                          to normalize threshold.
            threshold: the threshold to cross
        """

        ray_type = kwargs.get('ray_type', 'pupil')
        boundary_points = []
        spots_to_exclude = None

        if 'exclusion_center' in kwargs:
            exclusion_center = kwargs['exclusion_center']
            exclusion_radius = kwargs['exclusion_radius']
            if exclusion_center.any() != -1:
                im[int(exclusion_center[self.y_axis]) - int(exclusion_radius):
                   int(exclusion_center[self.y_axis]) + int(exclusion_radius),
                   int(exclusion_center[self.x_axis]) - int(exclusion_radius):
                   int(exclusion_center[self.x_axis]) + int(exclusion_radius)] = 0

        # create appropriately-centered rays
        rays_x = zero_referenced_rays[:, :, self.x_axis] + seed_point[self.x_axis]
        rays_y = zero_referenced_rays[:, :, self.y_axis] + seed_point[self.y_axis]

        # get the values from the image at each of the points
        vals = self._get_image_values(im, rays_x, rays_y)

        cutoff_index = int(cutoff_index)

        # define pupil and cr derivative cutoffs
        d_pup = 2
        d_cr = -5

        vals_slope = hstack((2 * ones([vals.shape[0], 1]), diff(vals, 1)))
        vals_slope[where(isnan(vals_slope))] = 0

        # Changes below made by MM.
        # scan inward-to-outward to find the first threshold crossing if looking
        # for cr need to find second threshold if looking at shrew pupil
        for r in range(0, vals.shape[0]):
            crossed = False

            for v in range(cutoff_index, vals.shape[1]):

                if isnan(v):
                    # End of ray reached
                    break

                val = vals[r, v]

                if ray_type == 'pupil':
                    if val > threshold:
                        crossed = True

                    # We want a more robust cutoff than just a positive or
                    # negative derivative. Set one much greater than zero
                    if crossed and vals_slope[r, v] >= d_pup:
                        boundary_points.append(array([rays_x[r, v - 1], rays_y[r, v - 1]]))
                        break

                if ray_type == 'cr':
                    # Stricter cutoff for cr reduced error
                    if threshold - 0.2*threshold < val < threshold + 0.2*threshold:
                        crossed = True

                    # We want a more robust cutoff than just a positive or
                    # negative derivative. Set one much less than zero
                    if crossed and vals_slope[r, v] <= d_cr:
                        boundary_points.append(array([rays_x[r, v - 1], rays_y[r, v - 1]]))
                        break

        return boundary_points
        # If these keywords are present in the input, we are excluding the region of the CR from the pupil search so
        # we can locate the pupil with the CR overlapping

        # if 'exclusion_center' in kwargs:
        #     final_boundary_points = []
        #     exclusion_center = kwargs['exclusion_center']
        #     exclusion_radius = kwargs['exclusion_radius']
        #
        #     if exclusion_center.any() == -1:
        #         return boundary_points
        #     else:
        #         for bp in boundary_points:
        #             if exclusion_center is None or linalg.norm(exclusion_center - bp) > exclusion_radius:
        #                 final_boundary_points.append(bp)
        #         return final_boundary_points
        # else:
        #     return boundary_points

    # def _find_ray_boundaries_woven(self, im, seed_point, zero_referenced_rays, cutoff_index, threshold, **kwargs):
    #     """ Find where a set off rays crosses a threshold in an image
    #
    #         Arguments:
    #         im -- An image (usually a gradient magnitude image) in which crossing will be found
    #         seed_point -- the origin from which rays will be projected
    #         zero_referenced_rays -- the set of rays (starting at zero) to sample.  nrays x ray_sampling x image_dimension
    #         cutoff_index -- the index along zero_referenced_rays below which we are sure that we are
    #                                 still within the feature.  Used to normalize threshold.
    #         threshold -- the threshold to cross, expressed in standard deviations across the ray samples
    #     """
    #
    #     # assert False
    #
    #     if 'exclusion_center' in kwargs:
    #         exclusion_center = kwargs['exclusion_center']
    #     else:
    #         exclusion_center = None
    #
    #     if 'exclusion_radius' in kwargs:
    #         exclusion_radius = kwargs['exclusion_radius']
    #     else:
    #         exclusion_radius = None
    #
    #     # create appropriately-centered rays
    #     rays_x = zero_referenced_rays[:, :, self.x_axis] + seed_point[self.x_axis]
    #     rays_y = zero_referenced_rays[:, :, self.y_axis] + seed_point[self.y_axis]
    #
    #     # get the values from the image at each of the points
    #     vals = self._get_image_values(im, rays_x, rays_y)
    #
    #     # We will return up to n_rays return indices
    #     returned_points = -1 * ones([zero_referenced_rays.shape[0], 2])
    #     # n_returned_points = 0
    #
    #     vals_slope = hstack((2 * ones([vals.shape[0], 1]), diff(vals, 1)))
    #     vals_slope[where(isnan(vals_slope))] = 0
    #     if not vals_slope.flags['C_CONTIGUOUS']:
    #         vals_slope = vals_slope.copy()
    #
    #     code = \
    #         """
    #
    #         // Get some array sizes
    #
    #         int n_rays = Nrays_x[0];
    #         int n_ray_samples = Nrays_x[1];
    #
    #
    #         // Compute normalization factors
    #         int n_vals = 0;
    #         double mean_val = 0;
    #         double var_val = 0;
    #         double old_mean = 0;
    #         double old_var = 0;
    #
    #
    #         // See Knuth TAOCP vol 2, 3rd edition, page 232
    #         // via http://www.johndcook.com/standard_deviation.html
    #         for(int r=0; r < n_rays; r++){
    #             for(int s=0; s < cutoff_index; s++){
    #                 int index = r*n_ray_samples + s;
    #                 double val = vals[index];
    #                 if(val != NAN){
    #                     n_vals++;
    #                     if(n_vals == 1){
    #                         old_mean = mean_val = val;
    #                         old_var = 0.0;
    #                     } else {
    #                         mean_val = old_mean + (val - old_mean)/n_vals;
    #                         var_val = old_var + (val - old_mean) * (val - mean_val);
    #
    #                         old_mean = mean_val;
    #                         old_var = var_val;
    #                     }
    #                 }
    #             }
    #         }
    #
    #         double std_val = sqrt(var_val/(n_vals-1));
    #
    #
    #
    #
    #
    #         double normalized_threshold = std_val * threshold + mean_val;
    #
    #         for(int r=0; r < n_rays; r++){
    #             short crossed = 0;
    #             for(int s=cutoff_index; s < n_ray_samples; s++){
    #                 int index = r*n_ray_samples + s;
    #                 double val = vals[index];
    #
    #                 if(val == NAN){
    #                     break; // end of ray
    #                 }
    #
    #                 if(val > normalized_threshold){
    #                     crossed = 1;
    #
    #                 }
    #
    #                 if(crossed && vals_slope[index] <= 0){
    #
    #                     returned_points[n_returned_points*2 + 0] = rays_x[r*n_ray_samples + s-1];
    #                     returned_points[n_returned_points*2 + 1] = rays_y[r*n_ray_samples + s-1];
    #                     n_returned_points++;
    #                     break;
    #                 }
    #             }
    #         }
    #     """
    #
    #     # inline(code_test, [n_returned_points])
    #
    #     inline(code, [
    #         'vals',
    #         'vals_slope',
    #         'rays_x',
    #         'rays_y',
    #         'cutoff_index',
    #         'threshold',
    #         'n_returned_points',
    #         'returned_points',
    #         ])
    #     boundary_points = []
    #
    #     for p in range(0, returned_points.shape[0]):
    #         if returned_points[p, 0] != -1.:
    #             bp = returned_points[p, :]
    #             if exclusion_center is None or linalg.norm(exclusion_center - bp) > exclusion_radius:
    #                 boundary_points.append(bp)
    #
    #     return boundary_points

    def _get_image_values_nearest(self, im, x_, y_):
        """ Sample an image at a set of x and y coordinates, using nearest
        neighbor interpolation.

        Args:
            im: [array] image
            x_: [float] pixel coordinate in x
            y_: [float] pixel coordinate in y

        Returns:
            vals: [array] sampled, interpolated image
        """

        x = x_.round()
        y = y_.round()

        # trim out-of-bounds elements
        bad_elements = where((x < 0) | (x >= im.shape[1]) | (y < 0) | (y >= im.shape[0]))

        x[bad_elements] = 0
        y[bad_elements] = 0

        vals = im[x.astype(int), y.astype(int)]
        vals[bad_elements] = nan
        return vals

    def _get_image_values_interp(self, im, x, y):
        """ Samples an image at a set of x and y coordinates, using bilinear
        interpolation

        Args:
            im: [array] image
            x: [float] pixel coordinate in x
            y: [float] pixel coordinate in y

        Returns:
            vals: [array] sampled, bilinearly interpolated image
        """

        vals = zeros(x.shape)
        floor_x = floor(x).astype(int)
        floor_y = floor(y).astype(int)
        ceil_x = ceil(x).astype(int)
        ceil_y = ceil(y).astype(int)

        x_frac = 1 - (x - floor_x)
        y_frac = 1 - (y - floor_y)

        for i in range(0, x.shape[0]):
            for j in range(0, x.shape[1]):
                if floor_x[i, j] < 0 or floor_y[i, j] < 0 or \
                        ceil_x[i, j] > im.shape[0] or \
                        ceil_y[i, j] > im.shape[1]:
                    vals[i, j] = nan
                    continue

                a = im[floor_x[i, j], floor_y[i, j]]
                b = im[ceil_x[i, j], floor_y[i, j]]
                c = im[floor_x[i, j], ceil_y[i, j]]
                d = im[ceil_x[i, j], ceil_y[i, j]]

                val = x_frac[i, j] * y_frac[i, j] * a + (1 - x_frac[i, j]) \
                    * y_frac[i, j] * b + x_frac[i, j] * (1 - y_frac[i, j]) * c \
                    + (1 - x_frac[i, j]) * (1 - y_frac[i, j]) * d

                vals[i, j] = val
        return vals

    def _get_image_values_interp_faster(self, im, x, y):
        """ Samples an image at a set of x and y coordinates, using bilinear
        interpolation (using no loops)

        Args:
            im: [array] image
            x: [float] pixel coordinate in x
            y: [float] pixel coordinate in y

        Returns:
            vals: [array] sampled, bilinearly interpolated image
        """

        # trim out-of-bounds elements
        bad_elements = where((x < 0) | (x >= im.shape[0] - 1) | (y < 0) | (y >= im.shape[1] - 1))

        # for now, put in zeros so that the computation doesn't fail
        x[bad_elements] = 0
        y[bad_elements] = 0

        vals = zeros(x.shape)
        floor_x = floor(x).astype(int)
        floor_y = floor(y).astype(int)
        ceil_x = ceil(x).astype(int)
        ceil_y = ceil(y).astype(int)

        x_frac = 1 - (x - floor_x)
        y_frac = 1 - (y - floor_y)

        a = im[floor_x, floor_y]
        b = im[ceil_x, floor_y]
        c = im[floor_x, ceil_y]
        d = im[ceil_x, ceil_y]

        vals = x_frac * y_frac * a + (1 - x_frac) * y_frac * b + x_frac * \
            (1 - y_frac) * c + (1 - x_frac) * (1 - y_frac) * d

        # invalidate out-of-bounds elements
        vals[bad_elements] = nan
        return vals

    def _fit_mean_to_points(self, points):
        """ Fit the center and radius of a set of points using the mean and std
        of the point cloud

        Args:
            points: [array] n x 2 array of the calculated points of pupil/CR
                    boundary

        Returns:
            center: [array] coordinates of the calculated center
            radius: [float] calculated radius
        """

        if points is None or len(points) == 0:
            return array([-1., -1.]), 0.0, Inf, 0.0, 0.0

        center = mean(points, 0)

        centered = array(points)
        centered[:, 0] -= center[0]
        centered[:, 1] -= center[1]
        distances = sqrt(centered[:, 0] ** 2 + centered[:, 1] ** 2)
        radius = mean(distances)

        return center, radius, 0.0, 0.0, 0.0

    def _fit_circle_to_points_lstsq(self, points):
        """ Fit a circle algebraically to a set of points, using least squares
        optimization

        Args:
            points: [array] n x 2 array of the calculated points of pupil/CR
                    boundary

        Returns:
            center: [array] coordinates of the calculated center
            radius: [float] calculated radius
            err: [float] fit error
        """

        if points is None or len(points) == 0:
            # print "_fit_circle_to_points_lstsq: no boundary points, bailing: ", points
            return array([-1., -1.]), 0.0, Inf, 0.0, 0.0

        if len(points) <= 3:
            return self._fit_mean_to_points(points)

        points_array = array(points)
        points_x = points_array[:, 0]
        points_x.shape = [prod(points_x.shape)]
        points_y = points_array[:, 1]
        points_y.shape = [prod(points_y.shape)]

        center_guess, radius_guess, dummy, _, _ = self._fit_mean_to_points(points)

        a0 = -2 * center_guess[0]
        b0 = -2 * center_guess[1]
        c0 = center_guess[0] ** 2 + center_guess[1] ** 2 - \
             (points_array[:, 0] - center_guess[0]).mean() ** 2
        p0 = array([a0, b0, c0])

        output = scipy.optimize.leastsq(self._residuals_circle, p0,
                                        args=(points_x, points_y))

        (a, b, c) = output[0]

        # Calculate the location of center and radius
        center_fit = array([-a / 2, -b / 2])
        radius_fit = sqrt(center_fit[0] ** 2 + center_fit[1] ** 2 - c)
        err = sum(self._residuals_circle(array([a, b, c]), points_x, points_y) ** 2)
        # print(err)
        return center_fit, radius_fit, err, 0.0, 0.0

    def _fit_ellipse_to_points(self, points):
        """
        Fits ellipse to the points found in self.find_ray_boundaries().
        Uses a bunch of linear algebra. If fitting fails, the function
        self._fit_ellipse_to_points_lstsq() is called instead.

        Args:
            points: [array] N x 2 array of coordinates for ray endpoints

        Returns: [tuple] ellipse centroid, radius (long axis), fit error,
                 rotation (in rads), short axis radius
        """

        if points is None or len(points) == 0:
            # print "_fit_ellipse_to_points_lstsq: no boundary points, bailing"
            return array([-1., -1.]), 0.0, Inf, 0.0, 0.0

        if len(points) < 5:
            return self._fit_mean_to_points(points)

        # initialize
        orientation_tolerance = 1e-3
        points_array = array(points)

        # remove bias of the ellipse - to make matrix inversion more accurate.
        # (will be added later on).
        x = points_array[:, 0]
        y = points_array[:, 1]
        mean_x = mean(x)
        mean_y = mean(y)
        x = x - mean_x
        y = y - mean_y

        # Make x and y column vectors
        x.shape = (size(x), 1)
        y.shape = (size(y), 1)

        # print "x no bias =", x

        # the estimation for the conic equation of the ellipse
        X = hstack((x ** 2, x * y, y ** 2, x, y))
        # print "X = ", X
        fit_err = 0

        try:
            A = dot(sum(X, axis=0), linalg.inv(dot(X.transpose(), X)))

        except linalg.LinAlgError:

            print 'A linear algebra error has occurred while ellipse fitting'
            return array([-1., -1.]), 0.0, Inf, 0.0, 0.0

        # extract parameters from the conic equation
        (a, b, c, d, e) = A
        # print a,b,c,d,e

        # remove the orientation from the ellipse
        if min(abs(b / a), abs(b / c)) > orientation_tolerance:
            # print "remove orientation"
            orientation_rad = 1 / 2 * arctan(b / (c - a))
            cos_phi = cos(orientation_rad)
            sin_phi = sin(orientation_rad)
            (a, b, c, d, e) = (a * cos_phi ** 2 - b * cos_phi * sin_phi + c * sin_phi ** 2,
                               0,
                               a * sin_phi ** 2 + b * cos_phi * sin_phi + c * cos_phi ** 2,
                               d * cos_phi - e * sin_phi,
                               d * sin_phi + e * cos_phi)
            (mean_x, mean_y) = (cos_phi * mean_x - sin_phi * mean_y,
                                sin_phi * mean_x + cos_phi * mean_y)
        else:
            orientation_rad = 0
            cos_phi = cos(orientation_rad)
            sin_phi = sin(orientation_rad)

        # print a,b,c,d,e

        # check if conic equation represents an ellipse
        test = a * c
        # if we found an ellipse return it's data
        if test > 0:

            # make sure coefficients are positive as required
            if a < 0:
                (a, c, d, e) = (-a, -c, -d, -e)

            # final ellipse parameters
            X0 = mean_x - d / 2 / a
            Y0 = mean_y - e / 2 / c
            F = 1 + d ** 2 / (4 * a) + e ** 2 / (4 * c)
            (a, b) = (sqrt(F / a), sqrt(F / c))
            long_axis = 2 * max(a, b)
            short_axis = 2 * min(a, b)

            # rotate the axes backwards to find the center point of the original TILTED ellipse
            R = array([[cos_phi, sin_phi], [-sin_phi, cos_phi]])
            P_in = dot(R, array([[X0], [Y0]]))
            X0_in = P_in[0]
            Y0_in = P_in[1]

            center_fit = array([X0_in[0], Y0_in[0]])

            # determine the fit error
            centered_points = points_array - ones((points_array.shape[0], 1)) * center_fit
            r_data = sqrt(centered_points[:, 0] ** 2 + centered_points[:, 1] ** 2)
            thetas = arctan(centered_points[:, 1] / centered_points[:, 0])
            r_fit = a * b / sqrt((b * cos(thetas)) ** 2 + a * sin(thetas) ** 2)
            fit_err = sum((r_fit - r_data) ** 2)

            # print "Estimated Ellipse center =", X0_in, Y0_in
            return center_fit, long_axis / 2.0, fit_err, orientation_rad, short_axis / 2.0

        elif test == 0:
            # print 'Error in ellipse fitting: parabola found instead of ellipse'
            return self._fit_circle_to_points_lstsq(points)
            # return (array([-1., -1.]), 0.0, Inf)
        elif test < 0:
            # print 'Error in ellipse fitting: hyperbola found instead of ellipse'
            return self._fit_circle_to_points_lstsq(points)
            # return (array([-1., -1.]), 0.0, Inf)

    def _fit_circle_to_points_lstsq_ransac(self, points):
        """ Fit a circle algebraically to a set of points, using least squares
        optimization with the RANSAC algorithm.

        Args:
            points: [array] n x 2 array of the calculated points of pupil/CR
                    boundary

        Returns:
            center: [array] coordinates of the calculated center
            radius: [float] calculated radius
            err: [float] fit error
        """

        max_iter = 20
        min_consensus = 8
        good_fit_consensus = round(len(points) / 2)
        pointwise_error_threshold = 0.05

        if len(points) < min_consensus:
            return self._fit_circle_to_points_lstsq(points)

        iter = 0
        # want to do better than this
        center_fit, radius_fit, best_err, _, _ = self._fit_circle_to_points_lstsq(points)

        while iter < max_iter:
            (maybe_inliers_i, the_rest_i) = self._random_split(len(points), min_consensus)
            maybe_inliers = []
            the_rest = []
            for i in maybe_inliers_i:
                maybe_inliers.append(points[i])
            for i in the_rest_i:
                the_rest.append(points[i])

            maybe_center, maybe_radius, maybe_err, _, _ = self._fit_circle_to_points_lstsq(maybe_inliers)

            for p in the_rest:
                dist = linalg.norm(p - maybe_center)
                point_err = abs(dist - maybe_radius)
                if point_err < pointwise_error_threshold * maybe_radius:
                    maybe_inliers.append(p)

            if len(maybe_inliers) > good_fit_consensus:
                candidate_center, candidate_radius, candidate_err, _, _ = \
                    self._fit_circle_to_points_lstsq(array(maybe_inliers))

                if candidate_err < best_err:
                    center_fit = candidate_center
                    radius_fit = candidate_radius
                    best_err = candidate_err

            iter += 1

        return center_fit, radius_fit, best_err, 0.0, 0.0

    def _random_split(self, n, k):
        r = random.rand(n)
        indices = argsort(r).astype(int)
        return indices[0:k], indices[k + 1:]

    def _residuals_circle(self, p, x, y):
        """ An objective function for fitting a circle function
        """

        (a, b, c) = p

        err = x ** 2 + y ** 2 + a * x + b * y + c
        return err


"""Everything below this line is test code to see if this class works."""
# A test script to see stuff in action
def test_ff_on_image(test_image):

    if len(test_image[0].shape) == 3:
        test_image = [mean(item, 2) for item in test_image]

    # add initial sobel filtered image as cached image
    starburst_ff = SubpixelStarburstEyeFeatureFinder(modality='2P', pupil_ray_length=45, pupil_threshold=40, cr_threshold=60)

    p_x = 65
    p_y = 65
    cr_x = 66
    cr_y = 71
    guess = {"pupil_position": array([p_y, p_x]), "cr_position": array([cr_y, cr_x])}

    """Note: need to enter modality type. Make this into drop down"""
    starburst_ff.analyze_image(test_image, guess)
    features = starburst_ff.get_result()

    # do it twice to allow compilation
    # starburst_ff.analyze_image(test_image, guess)
    # features = starburst_ff.get_result()

    return features

def adjust_gamma(image, gamma):
    # build a lookup table mapping the pixel values [0, 255] to
    # their adjusted gamma values
    invGamma = 1.0 / gamma
    table = array([((i / 255.0) ** invGamma) * 255 for i in arange(0, 256)]).astype("uint8")

    # apply gamma correction using the lookup table
    return cv2.LUT(image, table)

def adjust_image(image, gamma, contrast, brightness, mask):
    # adjust contrast and brightness
    image = image * contrast + brightness

    # Set thresholds
    image[image < 0] = 0
    image[image > 255] = 255
    image = image.astype('uint8')

    # adjust gamma
    image1 = cv2.bitwise_and(image.copy(), image, mask=mask)
    image1 = adjust_gamma(image1, gamma)

    # Equalize Histogram across the image to get pupil enhancement
    image1 = cv2.equalizeHist(image1)

    # Smooth image
    image1 = cv2.blur(image1, (5, 5))
    # el = [image1 != 0]
    # image[el] = image1[el]
    return image1

def plot_figs(orig_image, test_image, features, ellipse):
    starburst_ff = SubpixelStarburstEyeFeatureFinder(modality='2P', pupil_ray_length=45, pupil_threshold=30, cr_ray_length=10, cr_threshold=50)
    sobelified, _, _ = starburst_ff.sobel_cv(test_image)

    plt.figure()
    cv2.ellipse(orig_image, ellipse, 255, thickness=1)
    plt.subplot(1, 3, 1), plt.imshow(orig_image, interpolation='nearest', cmap='gray')
    frame1 = plt.gca()
    frame1.axes.get_xaxis().set_visible(False)
    frame1.axes.get_yaxis().set_visible(False)
    plt.title('Raw Image')

    plt.subplot(1, 3, 2), plt.imshow(test_image, interpolation='nearest')
    frame2 = plt.gca()
    frame2.axes.get_xaxis().set_visible(False)
    frame2.axes.get_yaxis().set_visible(False)
    plt.title('Gamma/Contrast Corrected')
    plt.gray()
    plt.hold(True)
    cr_position = features['cr_position']
    cr_radius = features['cr_radius']
    pupil_position = features['pupil_position']
    pupil_radius = features['pupil_radius']

    # plt.plot([cr_position[1]], [cr_position[0]], 'b+')
    # plt.plot([pupil_position[1]], [pupil_position[0]], 'b+')
    #
    sb = features['starburst']
    cr_bounds = sb['cr_boundary']
    pupil_bounds = sb['pupil_boundary']

    # for b in cr_bounds:
    #     plt.plot([b[1]], [b[0]], 'rx')
    #
    # for b in pupil_bounds:
    #     plt.plot([b[1]], [b[0]], 'gx')

    plt.subplot(1, 3, 3), plt.imshow(sobelified, interpolation='nearest', cmap='gray')
    frame3 = plt.gca()
    frame3.axes.get_xaxis().set_visible(False)
    frame3.axes.get_yaxis().set_visible(False)
    plt.title('Sobel filtered')
    cr_ray_start = sb['cr_rays_start']
    cr_ray_end = sb['cr_rays_end']

    pupil_ray_start = sb['pupil_rays_start']
    pupil_ray_end = sb['pupil_rays_end']

    for i in range(0, len(cr_ray_start)):
        plt.plot([cr_ray_start[i][1], cr_ray_end[i][1]], [cr_ray_start[i][0], cr_ray_end[i][0]], 'r-')
    for i in range(0, len(pupil_ray_start)):
        plt.plot([pupil_ray_start[i][1], pupil_ray_end[i][1]], [pupil_ray_start[i][0], pupil_ray_end[i][0]], 'b-')

    plt.plot(cr_position[1], cr_position[0], 'ro')
    for b in cr_bounds:
        plt.plot([b[1]], [b[0]], 'rx')

    plt.plot(pupil_position[1], pupil_position[0], 'go')
    for b in pupil_bounds:
        plt.plot([b[1]], [b[0]], 'gx')

    plt.figtext(.02, .07, 'CR position: (%.1f , %.1f). CR radius: %.1f px' % (cr_position[1], cr_position[0], cr_radius))
    plt.figtext(.02, .02, 'Pupil position: (%.1f , %.1f). Pupil radius: %.1f px' % (pupil_position[1], pupil_position[0], pupil_radius))

def main(im1, im2, mask):
    test_image1_adj = adjust_image(im1, 4, 3, 10, mask)
    test_image2_adj = adjust_image(im2, 4, 3, 10, mask)
    return test_ff_on_image([test_image1_adj, test_image2_adj]), test_image1_adj

def find_contour(im):
    _, im1 = cv2.threshold(im, 30, 255, type=cv2.THRESH_TOZERO_INV)
    im2 = cv2.Canny(im1, 35, 35)
    contours, heirarchy = cv2.findContours(im2.copy(), cv2.RETR_EXTERNAL, method=cv2.CHAIN_APPROX_NONE)
    edges = []
    # only want long contours
    for contour in contours:
        if contour.size > 250:
            c = vstack(contour)
            edges.append(c)
    # cv2.drawContours(im, edges[1:], -1, 255, 1)
    tot_e = concatenate(edges[1:], axis=0)
    ellipse = cv2.fitEllipse(tot_e)
    mask = zeros_like(im)
    return ellipse


if __name__ == '__main__':
    import matplotlib
    matplotlib.rcParams['pdf.fonttype'] = 42  # This is the crucial bit of code. The other stuff helps when you're trying to save TeX markup
    matplotlib.rcParams['font.family'] = 'sans-serif'
    matplotlib.rc('font', serif='Helvetica Neue')
    matplotlib.rc('text', usetex='false')
    matplotlib.rc('mathtext', fontset='custom')  # 'stix' also works for me.

    test_images = ['C:/users/mccannm/Desktop/Test_Data/test.png']

    for im in test_images:
        print im
        test_image1 = cv2.imread(im, 0)
        test_image2 = cv2.imread(im, 0)
        ellipse = find_contour(test_image1)
        mask = zeros_like(test_image1)
        cv2.ellipse(mask, ellipse, 255, thickness=-1)
        features, test_image1_adj = main(test_image1, test_image2, mask)
        plot_figs(test_image1, test_image1_adj, features, ellipse)

    plt.show()

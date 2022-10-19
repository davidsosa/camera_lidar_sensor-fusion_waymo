# ---------------------------------------------------------------------
# Project "Track 3D-Objects Over Time"
# Copyright (C) 2020, Dr. Antje Muntzinger / Dr. Andreas Haja.
#
# Purpose of this file : Data association class with single nearest neighbor association and gating based on Mahalanobis distance
#
# You should have received a copy of the Udacity license together with this program.
#
# https://www.udacity.com/course/self-driving-car-engineer-nanodegree--nd013
# ----------------------------------------------------------------------
#

# imports
import numpy as np
from scipy.stats.distributions import chi2

# add project directory to python path to enable relative imports
import os
import sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import misc.params as params
from typing import List

class Association:
    '''Data association class with single nearest neighbor association and gating based on Mahalanobis distance'''
    def __init__(self):
        self.association_matrix = np.matrix([])
        self.unassigned_tracks = []
        self.unassigned_measurements = []

    def associate(self, tracks: List, measurements: List, KF):

        ############
        # TODO Step 3: association:
        # - replace association_matrix with the actual association matrix based on Mahalanobis distance (see below) for all tracks and all measurements
        # - update list of unassigned measurements and unassigned tracks
        ############

        # the following only works for at most one track and one measurement
        self.association_matrix = np.matrix([]) # reset matrix
        self.unassigned_tracks = [] # reset lists
        self.unassigned_measurements = []

        if len(measurements) > 0:
            self.unassigned_measurements = [0]
        if len(tracks) > 0:
            self.unassigned_tracks = [0]
        if len(measurements) > 0 and len(tracks) > 0:
            self.association_matrix = np.matrix([[0]])

        ############
        # END student code
        ############

    def get_closest_track_and_meas(self):
        ############
        # TODO Step 3: find closest track and measurement:
        # - find minimum entry in association matrix
        # - delete row and column
        # - remove corresponding track and measurement from unassigned_tracks and unassigned_meas
        # - return this track and measurement
        ############

        # the following only works for at most one track and one measurement
        update_track = 0
        update_measurement = 0

        # remove from list
        self.unassigned_tracks.remove(update_track)
        self.unassigned_measurement.remove(update_measurement)
        self.association_matrix = np.matrix([])

        ############
        # END student code
        ############
        return update_track, update_measurement

    def gating(self, MHD, sensor):
        ############
        # TODO Step 3: return True if measurement lies inside gate, otherwise False
        ############

        pass

        ############
        # END student code
        ############

    def MHD(self, track, meas, KF):
        ############
        # TODO Step 3: calculate and return Mahalanobis distance
        ############

        pass

        ############
        # END student code
        ############

    def associate_and_update(self, manager, measurements, KF):
        # associate measurements and tracks
        self.associate(manager.tracks, measurements, KF)
        print("associate_and_update ")
        # update associated tracks with measurements
        while self.association_matrix.shape[0]>0 and self.association_matrix.shape[1]>0:

            # search for next association between a track and a measurement
            track_idx, measurement_idx = self.get_closest_track_and_measurement()
            if np.isnan(track_idx):
                print('---no more associations---')
                break
            track = manager.tracks[track_idx]

            if not measurements[0].sensor.in_fov(track.x):
                continue

            print('update track', track.id, 'with', measurements[measurement_idx].sensor.name,
                  'measurement', measurement_idx)
            KF.update(track, measurements[measurement_idx])
            manager.update_track(track)

            # save updated track
            manager.tracks[track_idx] = track

        # run track management
        manager.set_unassigned_tracks(self.unassigned_tracks)
        manager.set_unassigned_measurements(self.unassigned_measurements)
        manager.set_measurments_list(measurements)
        manager.manage_tracks()

        for track in manager.tracks:
            print('track', track.id, 'score =', track.score)
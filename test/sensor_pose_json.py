#!/usr/bin/env python
"""
Reads a set of data and labels from a group of sensors in a json file and calibrates the poses of these sensors.
"""

# -------------------------------------------------------------------------------
# --- IMPORTS (standard, then third party, then my own modules)
# -------------------------------------------------------------------------------
import json

import OptimizationUtils.OptimizationUtils as OptimizationUtils
import KeyPressManager.KeyPressManager as KeyPressManager
import OptimizationUtils.utilities as utilities
import numpy as np
import matplotlib.pyplot as plt
import plyfile as plyfile
import cv2
import argparse
import subprocess
import os
import shutil
from copy import deepcopy
from functools import partial
from matplotlib import cm
from scipy.spatial.distance import euclidean
from open3d import *

# -------------------------------------------------------------------------------
# --- FUNCTIONS
# -------------------------------------------------------------------------------

# -------------------------------------------------------------------------------
# --- MAIN
# -------------------------------------------------------------------------------
if __name__ == "__main__":

    # ---------------------------------------
    # --- Parse command line argument
    # ---------------------------------------
    ap = argparse.ArgumentParser()
    ap = OptimizationUtils.addArguments(ap)  # OptimizationUtils arguments
    ap.add_argument("-json", "--json_file", help="Json file containing input dataset.", type=str, required=True)
    args = vars(ap.parse_args())
    print("\nArgument list=")
    print(args)
    print('\n')

    # ---------------------------------------
    # --- INITIALIZATION
    # ---------------------------------------

    """ Loads a json file containing the detections"""
    f = open(args['json_file'], 'r')
    dataset = json.load(f)

    print(dataset)
    exit(0)

    # TODO output a report about the read json
    # print("\nDataset_cameras contains " + str(len(dataset_cameras.cameras)) + " cameras")

    # ---------------------------------------
    # --- Setup Optimizer
    # ---------------------------------------
    print('\nInitializing optimizer...')
    opt = OptimizationUtils.Optimizer()

    # TODO add model data. We can just include the super dictionary read from the json or convert it to a class first?
    # opt.addModelData('data_cameras', dataset_cameras)

    # ------------  Sensors -----------------
    # Each sensor will have a position (tx,ty,tz) and a rotation (r1,r2,r3)
    # TODO implement getters and setters for the sensor poses.

    # def getterCameraTranslation(data, cam_idx):
    #     return data.cameras[cam_idx].rgb.matrix[0:3, 3]
    #
    # def setterCameraTranslation(data, value, cam_idx):
    #     data.cameras[cam_idx].rgb.matrix[0:3, 3] = value
    #
    # def getterCameraRotation(data, cam_idx):
    #     matrix = data.cameras[cam_idx].rgb.matrix[0:3, 0:3]
    #     return utilities.matrixToRodrigues(matrix)
    #
    # def setterCameraRotation(data, value, cam_idx):
    #     matrix = utilities.rodriguesToMatrix(value)
    #     data.cameras[cam_idx].rgb.matrix[0:3, 0:3] = matrix

    # Add parameters related to the sensors
    # TODO create sensor pose related params
    # for cam_idx, camera in enumerate(dataset_cameras.cameras):
    #     # Add the translation
    #     opt.pushParamV3(group_name='C' + camera.name + '_t', data_key='data_cameras',
    #                     getter=partial(getterCameraTranslation, cam_idx=cam_idx),
    #                     setter=partial(setterCameraTranslation, cam_idx=cam_idx),
    #                     sufix=['x', 'y', 'z'])
    #
    #     # Add the rotation
    #     opt.pushParamV3(group_name='C' + camera.name + '_r', data_key='data_cameras',
    #                     getter=partial(getterCameraRotation, cam_idx=cam_idx),
    #                     setter=partial(setterCameraRotation, cam_idx=cam_idx),
    #                     sufix=['1', '2', '3'])

    # ------------  Chessboard -----------------
    # Each Chessboard will have the position (tx,ty,tz) and rotation (r1,r2,r3)
    # TODO add getter and setters for translation and rotation
    # TODO how to get the first guess for each chessboard pose?

    # def getterArucoTranslation(data, aruco_id):
    #     return data.arucos[aruco_id].matrix[0:3, 3]
    #
    # def setterArucoTranslation(data, value, aruco_id):
    #     data.arucos[aruco_id].matrix[0:3, 3] = value

    # Add parameters related to the Chessboards
    # for aruco_id, aruco in dataset_arucos.arucos.items():
    #     opt.pushParamV3(group_name='A' + str(aruco_id), data_key='data_arucos',
    #                     getter=partial(getterArucoTranslation, aruco_id=aruco_id),
    #                     setter=partial(setterArucoTranslation, aruco_id=aruco_id),
    #                     sufix=['_tx', '_ty', '_tz'])

    # opt.printParameters()

    # ---------------------------------------
    # --- Define THE OBJECTIVE FUNCTION
    # ---------------------------------------
    first_time = True


    def objectiveFunction(data):
        """
        Computes the vector of errors. There should be an error for each stamp, sensor and chessboard tuple.
        The computation of the error varies according with the modality of the sensor:
            - Reprojection error for camera to chessboard
            - Point to plane distance for 2D laser scanners
            - (...)
        :return: a vector of residuals
        """
        # Get the data
        # TODO get data from model
        # data_cameras = data['data_cameras']

        errors = []

        # TODO implement the error estimation. Here is what we must iterate
        # for collection in collections
        #       for sensor in sensors
        #           if chessboad detected by this sensor in collection
                        # compute the error
        #               errors.append(error)

        first_time = False

        # Return the errors
        return errors


    opt.setObjectiveFunction(objectiveFunction)

    # ---------------------------------------
    # --- Define THE RESIDUALS
    # ---------------------------------------
    # TODO residuals: each error is computed after the sensor and the chessboard of a collection.
    #  Thus, each error will be affected by the parameters tx,ty,tz,r1,r2,r3 of the sensor and the chessboar

    # for camera in dataset_cameras.cameras:
    #     for aruco_id, aruco_detection in camera.rgb.aruco_detections.items():
    #         params = opt.getParamsContainingPattern('C' + str(camera.name))
    #         params.extend(opt.getParamsContainingPattern('A' + str(aruco_id)))
    #         opt.pushResidual(name='C' + camera.name + 'A' + str(aruco_id), params=params)

    print('residuals = ' + str(opt.residuals))

    # ---------------------------------------
    # --- Compute the SPARSE MATRIX
    # ---------------------------------------
    opt.computeSparseMatrix()

    # ---------------------------------------
    # --- SETUP THE VISUALIZATION FUNCTION
    # ---------------------------------------
    # TODO we should plot the poses of the cameras and the chessboards in 3D,
    #  and perhaps the sensor data with the projections.

    if args['view_optimization']:
        # position the windows in the proper place
        for i, camera in enumerate(dataset_cameras.cameras):
            cv2.namedWindow('Cam ' + camera.name, cv2.WINDOW_NORMAL)
            cv2.moveWindow('Cam ' + camera.name, 300 * i, 50)
            cv2.imshow('Cam ' + camera.name, camera.rgb.image)

        fig = plt.figure()
        ax = fig.gca(projection='3d')

        ax.set_xlabel('X'), ax.set_ylabel('Y'), ax.set_zlabel('Z')
        ax.set_xticklabels([]), ax.set_yticklabels([]), ax.set_zticklabels([])
        limit = 1.5
        ax.set_xlim3d(-limit, limit), ax.set_ylim3d(-limit, limit), ax.set_zlim3d(-limit, limit)
        ax.view_init(elev=122, azim=-87)

        # Draw world axis
        world_T_world = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float)
        utilities.drawAxis3D(ax, world_T_world, "world", axis_scale=0.7, line_width=3)

        # Draw cameras
        for camera in dataset_cameras.cameras:
            camera.handle_frame = utilities.drawAxis3D(ax, camera.rgb.matrix, "C" + camera.name, axis_scale=0.3,
                                                       line_width=2)
            # print("camera " + camera.name + " " + str(camera.handle_frame))

        # Draw Arucos
        dataset_arucos.handles = {}
        for aruco_id, aruco in dataset_arucos.arucos.items():
            dataset_arucos.handles[aruco_id] = utilities.drawAxis3DOrigin(ax, aruco.matrix, 'A' + str(aruco_id),
                                                                          line_width=1.0,
                                                                          fontsize=8,
                                                                          handles=None)
            # print("aruco " + str(aruco_id) + "= " + str(dataset_arucos.handles[aruco_id]))

        wm = KeyPressManager.WindowManager(fig)
        if wm.waitForKey(time_to_wait=0.01, verbose=True):
            exit(0)


    # ---------------------------------------
    # --- DEFINE THE VISUALIZATION FUNCTION
    # ---------------------------------------
    def visualizationFunction(data):
        font = cv2.FONT_HERSHEY_SIMPLEX  # font for displaying text
        # Get the data
        data_cameras = data['data_cameras']
        data_arucos = data['data_arucos']

        # print("data_cameras\n" + str(data_cameras.cameras[0].rgb.matrix))

        for i, _camera in enumerate(data_cameras.cameras):
            image = deepcopy(_camera.rgb.image)
            # print("Cam " + str(camera.name))
            for _aruco_id, _aruco_detection in _camera.rgb.aruco_detections.items():
                # print("Aruco " + str(aruco_id))
                # print("Pixel center coords (ground truth) = " + str(aruco_detection.center))  # ground truth

                utilities.drawSquare2D(image, _aruco_detection.center[0], _aruco_detection.center[1], 10,
                                       color=(0, 0, 255), thickness=2)

                cv2.putText(image, "Id:" + str(_aruco_id), _aruco_detection.center, font, 1, (0, 255, 0), 2,
                            cv2.LINE_AA)

                # cv2.line(image, aruco_detection.center, aruco_detection.center, (0, 0, 255), 10)
                # print("Pixel center projected = " + str(aruco_detection.projected))  # ground truth

                if 0 < _aruco_detection.projected[0] < _camera.rgb.camera_info.width \
                        and 0 < _aruco_detection.projected[1] < _camera.rgb.camera_info.height:
                    x = int(_aruco_detection.projected[0])
                    y = int(_aruco_detection.projected[1])
                    # cv2.line(image, aruco_detection.projected, aruco_detection.projected, (255, 0, 0), 10)
                    cv2.line(image, (x, y), (x, y), (255, 0, 0), 10)

                # TODO: debug drawing first detection code
                if 0 < _aruco_detection.first_projection[0] < _camera.rgb.camera_info.width \
                        and 0 < _aruco_detection.first_projection[1] < _camera.rgb.camera_info.height:
                    x = int(_aruco_detection.first_projection[0])
                    y = int(_aruco_detection.first_projection[1])
                    # cv2.line(image, aruco_detection.first_projection, aruco_detection.first_projection, (0, 255, 0), 10)
                    cv2.line(image, (x, y), (x, y), (0, 255, 0), 10)

            cv2.imshow('Cam ' + _camera.name, image)

        # Draw camera's axes
        for _camera in data_cameras.cameras:
            utilities.drawAxis3D(ax=ax, transform=_camera.rgb.matrix, text="C" + _camera.name, axis_scale=0.3,
                                 line_width=2,
                                 handles=_camera.handle_frame)

        # Draw Arucos
        for _aruco_id, _aruco in data_arucos.arucos.items():
            utilities.drawAxis3DOrigin(ax, _aruco.matrix, 'A' + str(_aruco_id), line_width=1.0,
                                       handles=data_arucos.handles[_aruco_id])

        wm = KeyPressManager.WindowManager(fig)
        if wm.waitForKey(0.01, verbose=False):
            exit(0)


    opt.setVisualizationFunction(visualizationFunction, args['view_optimization'], niterations=10)

    # ---------------------------------------
    # --- Create X0 (First Guess)
    # ---------------------------------------
    # Already created when pushing the parameters

    # opt.x = opt.addNoiseToX(noise=0.1)
    # opt.fromXToData()
    # opt.callObjectiveFunction()

    # ---------------------------------------
    # --- Start Optimization
    # ---------------------------------------
    # print("\n\nStarting optimization")

    # This optimizes well
    opt.startOptimization(
        optimization_options={'x_scale': 'jac', 'ftol': 1e-5, 'xtol': 1e-5, 'gtol': 1e-5, 'diff_step': 1e-4})

    # opt.startOptimization(
    #    optimization_options={'x_scale': 'jac', 'ftol': 1e-5, 'xtol': 1e-5, 'gtol': 1e-5, 'diff_step': 1e-4,
    #                          'max_nfev': 1})

    # This optimized forever but was already at 1.5 pixels avg errror and going when I interrupted it
    # opt.startOptimization(optimization_options={'x_scale': 'jac', 'ftol': 1e-8, 'xtol': 1e-8, 'gtol': 1e-8, 'diff_step': 1e-4})

    print('\n-----------------')
    opt.printParameters(opt.x0, text='Initial parameters')
    print('\n')
    opt.printParameters(opt.xf, text='Final parameters')

    # ---------------------------------------
    # --- Save Results
    # ---------------------------------------
    # Todo should be saved back to a json or directly to xacro?

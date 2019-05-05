#!/usr/bin/env python
"""
This example shows an optimizer working with a set of n cameras, changing their pose so that the reprojection error is
minimized.
The OCDatasetLoader is used to collect data from a OpenConstructor dataset.
"""

# -------------------------------------------------------------------------------
# --- IMPORTS (standard, then third party, then my own modules)
# -------------------------------------------------------------------------------
import OCDatasetLoader.OCDatasetLoader as OCDatasetLoader
import OCDatasetLoader.OCArucoDetector as OCArucoDetector
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

##
# @brief Executes the command in the shell in a blocking or non-blocking manner
#
# @param cmd a string with teh command to execute
#
# @return
def bash(cmd, blocking=True):
    print("Executing command: " + cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if blocking:
        for line in p.stdout.readlines():
            print line,
        p.wait()


##
# @brief Writes out the ply header into the provided file object
#
# @param file_object the file object to write to
# @param num_vertex the number of vertices the file will have information for
#
# @return
def writePlyHeader(file_object, num_vertex):
    file_object.write('ply' + '\n')
    file_object.write('format ascii 1.0' + '\n')
    # file_object.write('comment ---' + '\n')
    file_object.write('element vertex ' + str(num_vertex) + '\n')
    # file_object.write('property float nx' + '\n')
    # file_object.write('property float ny' + '\n')
    # file_object.write('property float nz' + '\n')
    file_object.write('property float x' + '\n')
    file_object.write('property float y' + '\n')
    file_object.write('property float z' + '\n')
    file_object.write('property uchar red' + '\n')
    file_object.write('property uchar green' + '\n')
    file_object.write('property uchar blue' + '\n')
    # file_object.write('element face 0' + '\n')
    # file_object.write('property list uchar uint vertex_indices' + '\n')
    file_object.write('end_header' + '\n')


# -------------------------------------------------------------------------------
# --- MAIN
# -------------------------------------------------------------------------------
if __name__ == "__main__":

    # ---------------------------------------
    # --- Parse command line argument
    # ---------------------------------------
    ap = argparse.ArgumentParser()
    ap = OCDatasetLoader.addArguments(ap)  # Dataset loader arguments
    ap = OptimizationUtils.addArguments(ap)  # OptimizationUtils arguments
    args = vars(ap.parse_args())
    print("\nArgument list=")
    print(args)
    print('\n')

    # ---------------------------------------
    # --- INITIALIZATION
    # ---------------------------------------
    dataset_loader = OCDatasetLoader.Loader(args)
    dataset_cameras = dataset_loader.loadDataset()

    # print(dataset_cameras.cameras[0].rgb.stamp)
    # exit(0)

    aruco_detector = OCArucoDetector.ArucoDetector(args)
    dataset_arucos, dataset_cameras = aruco_detector.detect(dataset_cameras)
    print("\nDataset_cameras contains " + str(len(dataset_cameras.cameras)) + " cameras")


    # ---------------------------------------
    # --- Extract the rgb_T_depth and rgb_T_device transforms
    # ---------------------------------------
    # TODO we are using the final camera for computing depth_T_camera. It should be fixed but of course there will be
    #  slight variations because we infer it from a matrix multiplication. Should we average?

    for camera in dataset_cameras.cameras:
        world_T_camera= np.linalg.inv(camera.rgb.matrix)
        depth_T_world = camera.depth.matrix
        dataset_cameras.depth_T_camera = np.dot(world_T_camera, depth_T_world)

    for camera in dataset_cameras.cameras:
        world_T_camera= np.linalg.inv(camera.rgb.matrix)
        device_T_world = camera.matrix
        dataset_cameras.device_T_camera = np.dot(world_T_camera, device_T_world)
    # ---------------------------------------
    # --- Setup Optimizer
    # ---------------------------------------
    print('\nInitializing optimizer...')
    opt = OptimizationUtils.Optimizer()
    opt.addModelData('data_cameras', dataset_cameras)
    opt.addModelData('data_arucos', dataset_arucos)


    # ------------  Cameras -----------------
    # Each camera will have a position (tx,ty,tz) and a rotation (r1,r2,r3)
    # thus, the getter should return a list of size 6
    def getterCameraTranslation(data, cam_idx):
        return data.cameras[cam_idx].rgb.matrix[0:3, 3]


    def setterCameraTranslation(data, value, cam_idx):
        data.cameras[cam_idx].rgb.matrix[0:3, 3] = value


    def getterCameraRotation(data, cam_idx):
        matrix = data.cameras[cam_idx].rgb.matrix[0:3, 0:3]
        return utilities.matrixToRodrigues(matrix)


    def setterCameraRotation(data, value, cam_idx):
        matrix = utilities.rodriguesToMatrix(value)
        data.cameras[cam_idx].rgb.matrix[0:3, 0:3] = matrix


    # Add parameters related to the cameras
    for cam_idx, camera in enumerate(dataset_cameras.cameras):
        # Add the translation
        opt.pushParamV3(group_name='C' + camera.name + '_t', data_key='data_cameras',
                        getter=partial(getterCameraTranslation, cam_idx=cam_idx),
                        setter=partial(setterCameraTranslation, cam_idx=cam_idx),
                        sufix=['x', 'y', 'z'])

        # Add the rotation
        opt.pushParamV3(group_name='C' + camera.name + '_r', data_key='data_cameras',
                        getter=partial(getterCameraRotation, cam_idx=cam_idx),
                        setter=partial(setterCameraRotation, cam_idx=cam_idx),
                        sufix=['1', '2', '3'])


    # ------------  ArUcos -----------------
    # Each ArUco will only have the position (tx,ty,tz)
    # thus, the getter should return a list of size 3
    def getterArucoTranslation(data, aruco_id):
        return data.arucos[aruco_id].matrix[0:3, 3]


    def setterArucoTranslation(data, value, aruco_id):
        data.arucos[aruco_id].matrix[0:3, 3] = value


    # Add parameters related to the ArUcos
    for aruco_id, aruco in dataset_arucos.arucos.items():
        opt.pushParamV3(group_name='A' + str(aruco_id), data_key='data_arucos',
                        getter=partial(getterArucoTranslation, aruco_id=aruco_id),
                        setter=partial(setterArucoTranslation, aruco_id=aruco_id),
                        sufix=['_tx', '_ty', '_tz'])

    opt.printParameters()

    # ---------------------------------------
    # --- Define THE OBJECTIVE FUNCTION
    # ---------------------------------------
    first_time = True


    def objectiveFunction(data):
        """
        Computes the vector of errors. Each error is associated with a camera, ans is computed from the Euclidean distance
        between the projected coordinates of aruco centers and the coordinates given by the detection of the aruco in the image.
        :param data: points to the camera and aruco dataset
        :return: a vector of residuals
        """
        # Get the data
        data_cameras = data['data_cameras']
        data_arucos = data['data_arucos']

        errors = []

        # Cycle all cameras in the dataset
        for _camera in data_cameras.cameras:
            # print("Cam " + str(camera.name))
            for _aruco_id, _aruco_detection in _camera.rgb.aruco_detections.items():
                # print("Aruco " + str(aruco_id))
                # print("Pixel center coords (ground truth) = " + str(aruco_detection.center))  # ground truth

                # Find current position of aruco
                world_T_camera = np.linalg.inv(_camera.rgb.matrix)
                # print('world_to_camera = ' + str(world_T_camera))

                # Extract the translation from the transform matrix and create a np array with a 4,1 point coordinate
                aruco_origin_world = data_arucos.arucos[_aruco_id].matrix[0:4, 3]
                # print("aruco_origin_world = " + str(aruco_origin_world))

                # if int(aruco_id) == 579:
                #     print('ArUco 579 is in: ' + str(aruco_origin_world))

                aruco_origin_camera = np.dot(world_T_camera, aruco_origin_world)
                # print("aruco_origin_camera = " + str(aruco_origin_camera))

                pixs, valid_pixs, dists = utilities.projectToCamera(np.array(_camera.rgb.camera_info.K).reshape((3, 3)),
                                                                    _camera.rgb.camera_info.D,
                                                                    _camera.rgb.camera_info.width,
                                                                    _camera.rgb.camera_info.height,
                                                                    np.array(aruco_origin_camera,
                                                                             dtype=np.float).reshape((4, 1)))
                _aruco_detection.projected = (pixs[0][0], pixs[1][0])
                # if int(aruco_id) == 579:
                #     print('ArUco 579 is projected to : ' + str(aruco_detection.projected))

                global first_time
                if first_time:
                    _aruco_detection.first_projection = _aruco_detection.projected

                # print("aruco " + str(aruco_id) + " = " + str(aruco_detection.center))
                error = euclidean(_aruco_detection.center, _aruco_detection.projected)
                # print("error = " + str(error))
                # if error > 150:
                #     print(camera.name + 'is an outlier')
                errors.append(error)

        first_time = False
        # Return the errors
        return errors


    opt.setObjectiveFunction(objectiveFunction)

    # ---------------------------------------
    # --- Define THE RESIDUALS
    # ---------------------------------------
    for camera in dataset_cameras.cameras:
        for aruco_id, aruco_detection in camera.rgb.aruco_detections.items():
            params = opt.getParamsContainingPattern('C' + str(camera.name))
            params.extend(opt.getParamsContainingPattern('A' + str(aruco_id)))
            opt.pushResidual(name='C' + camera.name + 'A' + str(aruco_id), params=params)

    print('residuals = ' + str(opt.residuals))

    # ---------------------------------------
    # --- Compute the SPARSE MATRIX
    # ---------------------------------------
    opt.computeSparseMatrix()

    # ---------------------------------------
    # --- SETUP THE VISUALIZATION FUNCTION
    # ---------------------------------------
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
    # opt.startOptimization(
    #     optimization_options={'x_scale': 'jac', 'ftol': 1e-5, 'xtol': 1e-5, 'gtol': 1e-5, 'diff_step': 1e-4})

    opt.startOptimization(
        optimization_options={'x_scale': 'jac', 'ftol': 1e-5, 'xtol': 1e-5, 'gtol': 1e-5, 'diff_step': 1e-4,
                              'max_nfev': 1})

    # This optimized forever but was already at 1.5 pixels avg errror and going when I interrupted it
    # opt.startOptimization(optimization_options={'x_scale': 'jac', 'ftol': 1e-8, 'xtol': 1e-8, 'gtol': 1e-8, 'diff_step': 1e-4})

    print('\n-----------------')
    opt.printParameters(opt.x0, text='Initial parameters')
    print('\n')
    opt.printParameters(opt.xf, text='Final parameters')

    ################################################################################################################
    # Creating the optimized dataset
    print('\n---------------------------------------------------------------------------------------------------------')
    print('Creating optimized dataset...\n')

    # STEP 0
    # Compute the camera.depth.matrix usign the optimized camera.rgb.matrix and the depth_T_camera matrix (fixed)
    # print('\n\n\nDepth matrix before')
    # print(camera.depth.matrix)
    for camera in opt.data_models['data_cameras'].cameras:
        # TODO I don't understand why this multiplication should be like this. I have reached this through trial and
        #  error. Must be clarified

        # camera.depth.matrix =  np.dot(np.linalg.inv(opt.data_models['data_cameras'].depth_T_camera), np.linalg.inv(camera.rgb.matrix))
        camera.depth.matrix = np.dot(camera.rgb.matrix, opt.data_models['data_cameras'].depth_T_camera)

        camera.matrix = np.dot(camera.rgb.matrix, opt.data_models['data_cameras'].device_T_camera)

        # print('Depth matrix')
        # print(camera.depth.matrix)



    # STEP 1
    # Full copy of the dataset

    # Get the dest folder name
    if args['path_to_output_dataset'] is None:
        folders = args['path_to_images'].split('/')
        while '' in folders:
            folders.remove('')

        dataset_name = folders[-1]

        args['path_to_output_dataset'] = args['path_to_images'] + '/../' + dataset_name + '_optimized'

    # If an old version of the optimization exists
    if os.path.exists(args['path_to_output_dataset']):
        # Delete old folder
        shutil.rmtree(args['path_to_output_dataset'])

    # Create the new folder
    os.mkdir(args['path_to_output_dataset'])

    # Copy the images
    for camera in opt.data_models['data_cameras'].cameras:
        print()
        src = args['path_to_images'] + '/' + os.path.basename(camera.rgb.filename)
        dst = args['path_to_output_dataset'] + '/' + os.path.basename(camera.rgb.filename)
        shutil.copyfile(src, dst)

    # STEP 2
    # Overwrite txt files with new transform
    print('\nWriting new .txt files...')

    def p6d(s):
        """ Prints string with 6 decimal places """
        return "{0:.6f}".format(s)

    for camera in opt.data_models['data_cameras'].cameras:
        # print("\nCamera " + str(camera.name) + ':')

        world_T_camera_transposed = np.transpose(camera.rgb.matrix)
        # world_T_camera_transposed = np.linalg.inv(camera.rgb.matrix)
        world_T_depth_transposed = np.transpose(camera.depth.matrix)
        world_T_device_transposed = np.transpose(camera.matrix)

        # print("world_T_camera = " + str(world_T_camera_transposed))
        # print("world_T_depth = " + str(world_T_depth_transposed))

        txt_filename = args['path_to_output_dataset'] + '/' + camera.name.zfill(8) + '.txt'
        fh = open(txt_filename, 'w')

        # Write to file
        fh.write('3\n')

        for i in range(4):
            fh.write(p6d(world_T_camera_transposed[i][0]) + ' ' + p6d(world_T_camera_transposed[i][1]) + ' ' + p6d(
                world_T_camera_transposed[i][2]) + ' ' + p6d(world_T_camera_transposed[i][3]) + '\n')

        for i in range(4):
            fh.write(p6d(world_T_depth_transposed[i][0]) + ' ' + p6d(world_T_depth_transposed[i][1]) + ' ' + p6d(
                world_T_depth_transposed[i][2]) + ' ' + p6d(world_T_depth_transposed[i][3]) + '\n')

        for i in range(4):
            fh.write(p6d(world_T_device_transposed[i][0]) + ' ' + p6d(world_T_device_transposed[i][1]) + ' ' + p6d(
                world_T_device_transposed[i][2]) + ' ' + p6d(world_T_device_transposed[i][3]) + '\n')

        fh.write(str(camera.rgb.stamp))
        fh.close()
        print('Transformations writen to ' + txt_filename)

    # STEP 3
    # point clouds World to depth camera ref frame using old transform
    # then: point cloud from depth frame to world using new (optimized transform)

    # Colour map initialization
    cmap = cm.tab10(np.linspace(0, 1, 10))

    # Structure to hold all point clouds
    all_point_clouds = []
    all_old_point_clouds = []

    print("\nWriting new .ply files...")

    for cam_idx, camera in enumerate(dataset_cameras.cameras):

        # print('\nCamera ' + camera.name + ':')

        # Ply file corresponding to current camera
        ply_input_filename = args['path_to_images'] + '/' + camera.name.zfill(8) + '.ply'
        # print('Read pointcloud from ' + ply_input_filename)

        # Read vertices from point cloud
        imgData = plyfile.PlyData.read(ply_input_filename)["vertex"]
        num_vertex = len(imgData['x'])

        # Create array of read 3d points                      add 1 to make homogeneous
        xyz = np.c_[imgData['x'], imgData['y'], imgData['z'], np.ones(shape=(imgData['z'].size, 1))]
        # Create array of read normals                            add 1 to make homogeneous
        # nxyz = np.c_[imgData['nx'], imgData['ny'], imgData['nz'], np.ones(shape=(imgData['nz'].size, 1))]

        # print('Computing point cloud transformations...')

        # The local point clouds (ply files) are stored in openGL coordinates.
        opengl2opencv = np.zeros((4, 4))
        opengl2opencv[0, :] = [1, 0, 0, 0]
        opengl2opencv[1, :] = [0, 0, 1, 0]
        opengl2opencv[2, :] = [0, -1, 0, 0]
        opengl2opencv[3, :] = [0, 0, 0, 1]
        opencv2opengl = np.linalg.inv(opengl2opencv)

        old_world_T_depth = np.linalg.inv(camera.depth.matrix)

        depth_T_camera = dataset_cameras.depth_T_camera

        # This is after optimization
        camera_T_world = camera.rgb.matrix

        # Compute the transformation from the old openGL world to new openGL world
        # Convert from OpenGL to OpenCV: Apply opengl2opencv conversion
        # Go from world to depth through old transformation: Apply old_world_T_depth transformation
        # Go from depth to camera: Apply depth_T_camera transformation
        # Go from camera to new world: Apply optimized camera_T_world transformation
        T = np.dot(opencv2opengl,
                   np.dot(camera_T_world, np.dot(depth_T_camera, np.dot(old_world_T_depth, opengl2opencv))))

        pointsInNewWorld = np.transpose(np.dot(T, np.transpose(xyz)))

        # Use colour map on new point clouds
        r, g, b = (cmap[cam_idx % 10, 0:3] * 255)
        r, g, b = int(r), int(g), int(b)

        # Write to the .ply file
        ply_output_filename = args['path_to_output_dataset'] + '/' + camera.name.zfill(8) + '.ply'
        file_object = open(ply_output_filename, "w")

        # Write file header information
        writePlyHeader(file_object, num_vertex)

        # Write the new points
        for j in range(num_vertex):
            line = \
                str(pointsInNewWorld[j][0]) + ' ' + str(pointsInNewWorld[j][1]) + ' ' + str(pointsInNewWorld[j][2]) \
                + ' ' + \
                str(r) + ' ' + str(g) + ' ' + str(b) \
                + '\n'

            # str(normalsInNewWorld[j][0]) + ' ' + str(normalsInNewWorld[j][1]) + ' ' + str(normalsInNewWorld[j][2]) \
            # + ' ' + \

            # Write to ply file
            file_object.write(line)

            # Add line to merge
            all_point_clouds.append(line)

            # Get old line to merge clouds before optimization
            oldLine = \
                str(xyz[j][0]) + ' ' + str(xyz[j][1]) + ' ' + str(xyz[j][2]) \
                + ' ' + \
                str(r) + ' ' + str(g) + ' ' + str(b) \
                + '\n'

            # str(nxyz[j][0]) + ' ' + str(nxyz[j][1]) + ' ' + str(nxyz[j][2]) \
            # + ' ' + \

            all_old_point_clouds.append(oldLine)

        file_object.close()

        print('Pointcloud written to ' + ply_output_filename)

    ################################################################################################################
    # Merging pointclouds

    # Write to the .ply file
    ply_combined_output_filename = args['path_to_output_dataset'] + '/original_clouds.ply'
    file_object = open(ply_combined_output_filename, "w")

    # Write file header information
    writePlyHeader(file_object, str(len(all_old_point_clouds)))

    # Write the points
    for point_cloud in all_old_point_clouds:
        file_object.write(str(point_cloud))

    print('\nOriginal pointclouds merged to ' + ply_combined_output_filename)

    # Downsampling of combined point clouds
    # tmpPc = read_point_cloud(ply_combined_output_filename)
    # mergedOriginalPointClouds = voxel_down_sample(tmpPc, 0.05)
    # draw_geometries([mergedOriginalPointClouds])
    # write_point_cloud(ply_combined_output_filename, mergedOriginalPointClouds)
    # print('\nFile ' + ply_combined_output_filename + ' was downsampled')

    # Write to the .ply file
    ply_combined_output_filename = args['path_to_output_dataset'] + '/optimized_clouds.ply'
    file_object = open(ply_combined_output_filename, "w")

    # Write file header information
    writePlyHeader(file_object, str(len(all_point_clouds)))

    # Write the points
    for point_cloud in all_point_clouds:
        file_object.write(str(point_cloud))

    print('Optimized pointclouds merged to ' + ply_combined_output_filename)

    # Downsampling of combined point clouds
    # tmpPc = read_point_cloud(ply_combined_output_filename)
    # mergedOriginalPointClouds = voxel_down_sample(tmpPc, 0.05)
    # draw_geometries([mergedOriginalPointClouds])
    # write_point_cloud(ply_combined_output_filename, mergedOriginalPointClouds)
    # print('\nFile ' + ply_combined_output_filename + ' was downsampled')

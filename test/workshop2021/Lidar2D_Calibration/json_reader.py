#!/usr/bin/python3

import json
import pprint
import math
import matplotlib.pyplot as plt


def jsonImporter(path):
    """
    Imports .json file 
    Args:
        path: String

    Returns:

    """
    # Opening JSON file
    f = open(path, )
    data = json.load(f)
    return data


def divideDict(data, col):
    """
    Divides the data into the one from the left LIDAR and the right LIDAR
    """
    
    # Dividing the dictionary in two
    data_left = data['collections'][col]['data']['left_laser']
    data_right = data['collections'][col]['data']['right_laser']
    
    return data_left, data_right


def pol2cart(rho, phi):
    """
    Converts polar coordinates into cartesian coordinates
    Args:
        rho: Int
        phi: Int

    Returns:

    """
    x = rho * math.cos(phi)
    y = rho * math.sin(phi)
    return x, y


def dataTreatment(data_left, data_right):
    """
    From the data of both LIDARs, saves them on two lists of tuples
    Args:
        data_left: Dict
        data_right: Dict

    Returns:

    """

    # Retrieving data from the dictionary
    minangle_l = data_left['angle_min']
    maxangle_l = data_left['angle_max']
    incangle_l = data_left['angle_increment']
    minangle_r = data_right['angle_min']
    maxangle_r = data_right['angle_max']
    incangle_r = data_right['angle_increment']
    left_ranges = data_left['ranges']
    right_ranges = data_right['ranges']

    # Defining variables
    angle_left = minangle_l
    angle_right = maxangle_r
    minangleav_l = minangle_l + math.pi/4
    maxangleav_r = maxangle_r - math.pi/4
    left_xs = []
    left_ys = []
    right_xs = []
    right_ys = []

    # Converting from polar coordinates to cartesian coordinates
    for laser_range in left_ranges:
        if angle_left >= minangleav_l:
            x, y = pol2cart(laser_range, angle_left)
            left_xs.append(x)
            left_ys.append(y)
        angle_left += incangle_l

    for laser_range in right_ranges:
        if angle_right <= maxangleav_r:
            x, y = pol2cart(laser_range, angle_right)
            right_xs.append(x)
            right_ys.append(y)
        angle_right -= incangle_r

    return left_xs, left_ys, right_xs, right_ys

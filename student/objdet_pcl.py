# ---------------------------------------------------------------------
# Project "Track 3D-Objects Over Time"
# Copyright (C) 2020, Dr. Antje Muntzinger / Dr. Andreas Haja.
#
# Purpose of this file : Process the point-cloud and prepare it for object detection
#
# You should have received a copy of the Udacity license together with this program.
#
# https://www.udacity.com/course/self-driving-car-engineer-nanodegree--nd013
# ----------------------------------------------------------------------

# general package imports
import cv2
import numpy as np
import torch
import open3d
# add project directory to python path to enable relative imports
import os
import sys
from enum import Enum
import zlib

PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

# waymo open dataset reader
from tools.waymo_reader.simple_waymo_open_dataset_reader import utils as waymo_utils
from tools.waymo_reader.simple_waymo_open_dataset_reader import dataset_pb2, label_pb2

# object detection tools and helper functions
import misc.objdet_tools as tools

class RANGE_IMAGE_CELL_CHANNELS(Enum):
    RANGE = 0
    INTENSITY = 1
    ELONGATION = 2
    IS_IN_NO_LABEL_ZONE = 3

def show_pcl(pcl):
    print("student task ID_S1_EX2")
    vis = open3d.visualization.VisualizerWithKeyCallback()
    vis.create_window()
    pcd = open3d.geometry.PointCloud()
    # Remove intensity channel
    pcl = pcl[:,:-1]
    pcd.points = open3d.utility.Vector3dVector(pcl)
    open3d.visualization.draw_geometries([pcd])


def crop_channel_azimuth(img_channel, division_factor):
    opening_angle = int(img_channel.shape[1] / division_factor)
    img_channel_center = int(img_channel.shape[1] / 2)
    img_channel = img_channel[:, img_channel_center - opening_angle : img_channel_center + opening_angle]
    return img_channel


def load_range_image(frame, lidar_name):
    # get laser data structure from frame
    lidar = [obj for obj in frame.lasers if obj.name == lidar_name][0]
    range_image = []
    # use first response
    if len(lidar.ri_return1.range_image_compressed) > 0:
        range_image = dataset_pb2.MatrixFloat()
        range_image.ParseFromString(zlib.decompress(lidar.ri_return1.range_image_compressed))
        range_image = np.array(range_image.data).reshape(range_image.shape.dims)

    return range_image

def contrast_adjustment(img):
    return np.amax(img)/2 * img * 255 / (np.amax(img) - np.amin(img))

def map_to_8bit(range_image, channel):
    img_channel = range_image[:,:,channel]

    if channel == RANGE_IMAGE_CELL_CHANNELS.RANGE.value:
        img_channel = img_channel * 255 / (np.amax(img_channel) - np.amin(img_channel))
    elif channel == RANGE_IMAGE_CELL_CHANNELS.INTENSITY.value:
        img_channel = contrast_adjustment(img_channel)

    img_channel = img_channel.astype(np.uint8)
    return img_channel

def get_selected_channel(frame, lidar_name, channel):
    range_image = load_range_image(frame, lidar_name)
    range_image[range_image<0] = 0.0

    img_selected = map_to_8bit(range_image, channel = channel.value)
    #img_selected = crop_channel_azimuth(img_selected, division_factor=8)
    return img_selected

def show_range_image(frame, lidar_name):
    print("student task ID_S1_EX1")
    img_channel_range = get_selected_channel(frame, lidar_name, RANGE_IMAGE_CELL_CHANNELS.RANGE)
    img_channel_intensity = get_selected_channel(frame, lidar_name, RANGE_IMAGE_CELL_CHANNELS.INTENSITY)
    img_range_intensity = np.vstack([img_channel_range, img_channel_intensity])
    return img_range_intensity

def crop_point_cloud(lidar_pcl, config):
    lim_x = config.lim_x
    lim_y = config.lim_y
    lim_z = config.lim_z

    mask = np.where((lidar_pcl[:, 0] >= lim_x[0]) & (lidar_pcl[:, 0] <= lim_x[1]) &
                    (lidar_pcl[:, 1] >= lim_y[0]) & (lidar_pcl[:, 1] <= lim_y[1]) &
                    (lidar_pcl[:, 2] >= lim_z[0]) & (lidar_pcl[:, 2] <= lim_z[1]))

    lidar_pcl = lidar_pcl[mask]

    return lidar_pcl

# create birds-eye view of lidar data

def discretize_for_bev(lidar_pcl, configs):
    bev_discret = (configs.lim_x[1] - configs.lim_x[0]) / configs.bev_height
    lidar_pcl_cpy = np.copy(lidar_pcl)
    # remove lidar points outside detection area and with too low reflectivity
    lidar_pcl_cpy = crop_point_cloud(lidar_pcl_cpy, configs)
    ## step 2 : create a copy of the lidar pcl and transform all metrix x-coordinates into bev-image coordinates
    lidar_pcl_cpy[:, 0] = np.int_(np.floor(lidar_pcl_cpy[:, 0] / bev_discret))
    # step 3 : perform the same operation as in step 2 for the y-coordinates but make sure that no negative bev-coordinates occur
    lidar_pcl_cpy[:, 1] = np.int_(np.floor(lidar_pcl_cpy[:, 1] / bev_discret) + (configs.bev_width + 1) / 2)
     # step 4 : visualize point-cloud using the function show_pcl from a previous task
    lidar_pcl_cpy[:, 2] = lidar_pcl_cpy[:, 2] - configs.lim_z[0]

    return lidar_pcl_cpy

def draw_1D_map(custom_map, name):
    custom_map = custom_map * 256
    custom_map = custom_map.astype(np.uint8)
    while (1):
        cv2.imshow(name, custom_map)
        if cv2.waitKey(10) & 0xFF == 27:
            break
    cv2.destroyAllWindows()

def get_intensity_map_from_pcl(lidar_pcl, configs):
    lidar_pcl_cpy[lidar_pcl_cpy[:,3]>1.0, 3] = 1.0

    idx_intensity = np.lexsort((-lidar_pcl_cpy[:, 3], lidar_pcl_cpy[:, 1], lidar_pcl_cpy[:, 0]))
    lidar_pcl_cpy = lidar_pcl_cpy[idx_intensity]

    _, indices, count = np.unique(lidar_pcl_cpy[:, 0:2], axis=0, return_index=True, return_counts=True)
    lidar_pcl_int = lidar_pcl_cpy[indices]

    intensity_map = np.zeros((configs.bev_height + 1, configs.bev_width + 1))
    intensity_map[np.int_(lidar_pcl_int[:, 0]), np.int_(lidar_pcl_int[:, 1])] = \
        lidar_pcl_int[:, 3] / (np.amax(lidar_pcl_int[:, 3]) - np.amin(lidar_pcl_int[:, 3]))


def get_height_map_from_pcl(lidar_pcl, configs):
    height_map = np.zeros((configs.bev_height + 1, configs.bev_width + 1))

    idx_height = np.lexsort((-lidar_pcl_cpy[:, 2], lidar_pcl_cpy[:, 1], lidar_pcl_cpy[:, 0]))
    lidar_pcl_top = lidar_pcl_cpy[idx_height] # this has the highest point for each x, y coordinate
    _, idx_height_unique = np.unique(lidar_pcl_top[:, 0:2], axis=0, return_index=True)
    lidar_pcl_top = lidar_pcl_top[idx_height_unique]

    height_map[np.int_(lidar_pcl_top[:, 0]), np.int_(lidar_pcl_top[:, 1])] = \
        lidar_pcl_top[:, 2] / float(np.abs(configs.lim_z[1] - configs.lim_z[0]))


def get_density_map_from_pcl(lidar_pcl, configs):
    # Compute density layer of the BEV map
    density_map = np.zeros((configs.bev_height + 1, configs.bev_width + 1))
    _, _, counts = np.unique(lidar_pcl_cpy[:, 0:2], axis=0, return_index=True, return_counts=True)
    normalizedCounts = np.minimum(1.0, np.log(counts + 1) / np.log(64))
    density_map[np.int_(lidar_pcl_top[:, 0]), np.int_(lidar_pcl_top[:, 1])] = normalizedCounts

    return density_map


def assemble_bev_from_maps(density_map, intensity_map, height_map):
    # assemble 3-channel bev-map from individual maps
    bev_map = np.zeros((3, configs.bev_height, configs.bev_width))
    bev_map[2, :, :] = density_map[:configs.bev_height, :configs.bev_width]  # r_map
    bev_map[1, :, :] = height_map[:configs.bev_height, :configs.bev_width]  # g_map
    bev_map[0, :, :] = intensity_map[:configs.bev_height, :configs.bev_width]  # b_map

    # expand dimension of bev_map before converting into a tensor
    s1, s2, s3 = bev_map.shape
    bev_maps = np.zeros((1, s1, s2, s3))
    bev_maps[0] = bev_map

    bev_maps = torch.from_numpy(bev_maps)  # create tensor from birds-eye view
    input_bev_maps = bev_maps.to(configs.device, non_blocking=True).float()

    return input_bev_maps

def bev_from_pcl(lidar_pcl, configs, vis=False):
    ####### ID_S2_EX1 START #######
    print("student task ID_S2_EX1")
    lidar_pcl_cpy = discretize_for_bev(lidar_pcl, configs)
    ####### ID_S2_EX1 END #######
    ####### ID_S2_EX2 START #######
    print("student task ID_S2_EX2")
    intensity_map = get_intensity_map_from_pcl(lidar_pcl_cpy, configs)
    if vis:
        draw_1D_map(intensity_map, "intensity_map")
    ####### ID_S2_EX2 END #######
    ####### ID_S2_EX3 START #######
    print("student task ID_S2_EX3")
    height_map = get_height_map_from_pcl(lidar_pcl_cpy, configs)
    if vis:
        draw_1D_map(height_map, "height_map")
    ####### ID_S2_EX3 END #######
    density_map = get_density_map_from_pcl(lidar_pcl, configs):

    # Assemble BEV from maps
    input_bev_maps = assemble_bev_from_maps(density_map, intensity_map, height_map)

    return input_bev_maps



import ffmpeg
import cv2
import numpy as np
from geopy.distance import geodesic
from scipy.optimize import minimize

import json
import os
import shutil
import sys
import subprocess
import time
from decimal import Decimal
from typing import List

import gpmf.io as io
import gpmf.gps as gps

import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')

from datetime import datetime, timedelta
import time
import pandas as pd

time_format = r"%Y-%m-%d %H:%M:%S.%f"

def clean_times(blocks):
    """ cleans times """
    # print(*[(x.timestamp, x.precision) for x in blocks], sep='\n')
    date_time = datetime.strptime(blocks[-1].timestamp, time_format)
    # date_times = [datetime.strptime(x.timestamp, time_format) for x in blocks]
    # print(*date_times,sep='\n')
    # print(*[(x-y).total_seconds() for x,y in zip(date_times[1:], date_times[:len(date_times)-1])])
    # print()
    date = blocks[-1].timestamp.split(" ")[0]
    ret = []

    for x in blocks:
        if (date_time - datetime.strptime(x.timestamp,time_format)).total_seconds() > 3600: continue
        ret.append(
            gps.GPSData(
                description=x.description,
                timestamp=f"{date} {x.timestamp.split(' ')[1]}",
                samples_delivered=x.samples_delivered,
                precision=x.precision,
                fix=x.fix,
                latitude=x.latitude,
                longitude=x.longitude,
                altitude=x.altitude,
                speed_2d=x.speed_2d,
                speed_3d=x.speed_3d,
                units=x.units,
                npoints=x.npoints
            )
        )
    return ret


def get_gps_block_list(vid):
    """ gets the gps blocks using gpmf """
    # Read the binary stream from the file
    stream = io.extract_gpmf_stream(vid)

    # Extract GPS low level data from the stream
    gps_blocks = gps.extract_gps_blocks(stream)

    # Parse low level data into more usable format
    block_list = list(map(gps.parse_gps_block, gps_blocks))

    # clean times
    # return clean_times(block_list)
    return block_list


def get_t0_and_first_movement_times(gps_blocks):
    """ returns the t0 datetime and time in seconds of first movement """

    t0 = -1
    first_movement = -1
    date = gps_blocks[-1].timestamp.split(" ")[0] # yyyy-mm-dd
    for block in gps_blocks:
        if date not in block.timestamp: continue
        if t0 == -1 and block.precision < 50:
            t0 = datetime.strptime(block.timestamp, r"%Y-%m-%d %H:%M:%S.%f")
            first_movement = block.microseconds
        # latitude_movement = [x != y for x,y in zip(block.latitude[1:],block.latitude[:len(block.latitude)-1])]
        # longitude_movement = [x != y for x,y in zip(block.latitude[1:],block.latitude[:len(block.latitude)-1])]
        # movement = [x and y for x,y in zip(latitude_movement, longitude_movement)]
        # if first_movement == -1 and any(movement) and block.precision < 99:
        #     pass
        # # break
    
    return t0, first_movement


def distance_loss(lat_long1,lat_long2):
    return sum([geodesic(x,y).m for x,y in zip(lat_long1,lat_long2)])

def loss_function(offset, lat_long_vid1, lat_long_vid2):
    offset = int(offset)
    # print(lat_long_vid1,lat_long_vid2)
    slice_length = min(len(lat_long_vid1), len(lat_long_vid2))

    ret = distance_loss(lat_long_vid1, lat_long_vid2[offset:])
    print(ret)
    return ret


def align_videos(vid1, vid2, vid3):
    """ takes in two videos, defines an offset that aligns the two based on motion """

    gps_blocks_vid1 = get_gps_block_list(vid1)
    gps_blocks_vid2 = get_gps_block_list(vid2)
    gps_blocks_vid3 = get_gps_block_list(vid3)


    # lat_long_vid1 = []
    # lat_long_vid2 = []
    # for x in gps_blocks_vid1:
    #     lat_long_vid1 = lat_long_vid1 + [(x,y) for x,y in zip(x.latitude.tolist(),x.longitude.tolist())]

    # for x in gps_blocks_vid2:
    #     lat_long_vid2 = lat_long_vid2 + [(x,y) for x,y in zip(x.latitude.tolist(), x.longitude.tolist())]

    # lat_diff1 = np.array([x-y for x,y in zip([l[0] for l in lat_long_vid1[1:]],[l[0] for l in lat_long_vid1[:len(lat_long_vid1)-1]])])
    # lat_diff2 = np.array([x-y for x,y in zip([l[0] for l in lat_long_vid2[1:]],[l[0] for l in lat_long_vid2[:len(lat_long_vid2)-1]])])
    # long_diff1 = np.array([x-y for x,y in zip([l[1] for l in lat_long_vid1[1:]],[l[1] for l in lat_long_vid1[:len(lat_long_vid1)-1]])])
    # lat_long_diff1 = np.array([geodesic(x,y).m for x,y in zip(lat_long_vid1[1:],lat_long_vid1[:len(lat_long_vid1)-1])])
    # lat_long_diff2 = np.array([geodesic(x,y).m for x,y in zip(lat_long_vid2[1:],lat_long_vid2[:len(lat_long_vid2)-1])])

    # sign1 = np.sign(lat_diff1)
    # sign2 = np.sign(lat_diff2)
    # sum_sign1 = np.cumsum(sign1)
    # sum_sign2 = np.cumsum(sign2)
    
    # max_sum_sign1 = sum_sign1.tolist().index(max(sum_sign1))
    # max_sum_sign2 = sum_sign2.tolist().index(max(sum_sign2))

    # print(max_sum_sign2-max_sum_sign1)

    # sum_sign2 = sum_sign2[max_sum_sign2-max_sum_sign1:]

    # max_offset = 2*(max_sum_sign2-max_sum_sign1)
    # loss = 999999999999
    # for i in range(max_offset//2):
    #     new_loss = loss_function(i, 
    #                              lat_long_vid1[(len(lat_long_vid1)//2)-max_offset:(len(lat_long_vid1)//2)+max_offset], 
    #                              lat_long_vid2[(len(lat_long_vid2)//2)-2*max_offset:(len(lat_long_vid2)//2)+2*max_offset])
    #     if new_loss < loss:
    #         offset=i
    #         loss = new_loss

    # print(offset, loss)
    # plt.plot(sum_sign1)
    # plt.plot(sum_sign2)
    # plt.legend(loc='upper right')
    # # plt.savefig("lat_diff.png")
    # plt.show()


    # offset = 0
    # minimum = minimize(
    #     loss_function,
    #     x0 = offset,
    #     args=(lat_long_vid1[(len(lat_long_vid1)//2)-max_offset:(len(lat_long_vid1)//2)+max_offset], \
    #           lat_long_vid2[(len(lat_long_vid2)//2)-2*max_offset:(len(lat_long_vid2)//2)+2*max_offset]),
    #     method='Nelder-Mead',
    # )
        

    vid1_start_time, vid1_first_movement_time = get_t0_and_first_movement_times(gps_blocks_vid1)
    vid2_start_time, vid2_first_movement_time = get_t0_and_first_movement_times(gps_blocks_vid2)
    vid3_start_time, vid3_first_movement_time = get_t0_and_first_movement_times(gps_blocks_vid3)

    print(vid1_start_time, vid1_first_movement_time)
    print(vid2_start_time, vid2_first_movement_time)
    print(vid3_start_time, vid3_first_movement_time) 

    vid1_start_time = vid1_start_time - timedelta(seconds=vid1_first_movement_time/1e6)   
    vid2_start_time = vid2_start_time - timedelta(seconds=vid2_first_movement_time/1e6)   
    vid3_start_time = vid3_start_time - timedelta(seconds=vid3_first_movement_time/1e6)



    times = [vid1_start_time, vid2_start_time, vid3_start_time]
    print(*times,sep='\n')
    cameras = ['bottom', 'nadir', 'oblique']

    max_time = max(vid1_start_time, vid2_start_time, vid3_start_time)
    max_camera = cameras[times.index(max_time)]

    time_diff = [abs((x - max_time).total_seconds()) for x in times]
    frame_rate = 120 # frames per second
    time_diff_in_frames = [frame_rate * x for x in time_diff]

    offsets = {
        cameras[i]: int(time_diff_in_frames[i]) + 120 for i in range(len(cameras))
    }
    with open('offsets.json', 'w') as outfile:
        json.dump(offsets, outfile)

    print(offsets)
    print(time_diff)

    


if __name__ == "__main__":

    bottom_vid = "videos/bottom.mp4"
    nadir_vid = "videos/nadir.mp4"
    oblique_vid = "videos/oblique.mp4"

    align_videos(bottom_vid, nadir_vid, oblique_vid)
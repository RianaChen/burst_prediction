#!/#!/usr/bin/env python
# coding=utf-8

# find burst

import numpy as np
import scipy
import csv
import json
import sys

from scipy.signal import argrelextrema


def check_up_slope(arr, start, end, point, st_p):
    win_size = 30
    deviation = max(np.std(arr[start:end]), np.std(arr[st_p:]) / 2.0)
    angle = 0.5 * np.std(arr[st_p:]) / win_size
    if (arr[point] - arr[start]) / (point - start) >= angle and arr[point] - arr[start] >= deviation:
        return True
    else:
        return False

def check_down_slope(arr, start, end, point, st_p):
    win_size = 30
    deviation = max(np.std(arr[start:end]), np.std(arr[st_p:]) / 2.0)
    angle = 0.5 * np.std(arr[st_p:]) / win_size
    if (arr[end] - arr[point]) / (end - point) >= angle and arr[point] - arr[end] >= deviation:
        return True
    else:
        return False


def combine_bursts(arr, top1, top2, start, end1, end2):
    threshold_length = 15  # can be changed
    length1 = end1 - top1
    length2 = top2 - end1
    height_diff1 = arr[top1] - arr[end1]
    height_diff2 = arr[top2] - arr[end1]

    return_value = 0
    # return 1: change burst end
    # return 2: change burst top
    # return 3: change both
    if arr[top2] > arr[top1] and arr[start] < arr[end1]:
        if height_diff1 <= arr[top1] / 10.0 or length1 <= threshold_length:
            return_value += 1
    if arr[top2] <= arr[top1] and arr[end1] > arr[end2]:
        if height_diff2 <= arr[top1] / 10.0 or length2 <= threshold_length:
            return_value += 1

    if height_diff1 < height_diff2 and height_diff1 / (top1 - start) < height_diff2 / (top2 - start):
        return_value += 2

    return return_value


# load data
series = np.genfromtxt(sys.argv[1], delimiter=",")
start_points = np.genfromtxt(sys.argv[2], delimiter=",")
m, n = series.shape

# save data
burst_writer = csv.writer(open(sys.argv[3], "w"), delimiter=";")
max_writer = csv.writer(open(sys.argv[4], "w"), delimiter=",")
min_writer = csv.writer(open(sys.argv[5], "w"), delimiter=",")

for i in xrange(0, m):
    # for argrelextrema algorithm
    for j in xrange(0, n - 1):
        if series[i][j + 1] == series[i][j]:
            series[i][j + 1] += 0.001

    # ignore dates with no record
    st_p = int(start_points[i])

    # find local mins and local maxs
    local_min = [date for date in argrelextrema(series[i], np.less)[0] if date >= st_p]
    local_max = [date for date in argrelextrema(series[i], np.greater)[0] if date >= st_p]

    # save local mins and maxs
    # np.savetxt(sys.argv[2], local_min, delimiter=",")
    max_writer.writerow(local_max)
    min_writer.writerow(local_min)

    # use local mins to find burst
    # 1. define a window size
    # 2. if |t_0 - local_min| > win_size, then refind the local_min in win_size
    # 3. use slope and delta y between y_t0 & y_localmin to find the burst
    #    if delta y keep increasing and slope too, meaning here comes a burst
    #    if delta y and slope stop increasing, find the burst point.

    # burst data structure: (start time, end time, burst point, burst_y)
    burst = []
    max_min = 0

    if len(local_min) <= 0 or len(local_max) <= 0:
        burst_writer.writerow(burst)
        continue

    # if t_localmax[0] < t_localmin[0], recognize it as first burst
    if local_max[0] < local_min[0]:
        max_min = 1
        if check_up_slope(series[i], 0, 2 * local_max[0], local_max[0], st_p):
            burst.append((0, min(local_min[
                1], 2 * local_max[0]), local_max[0], series[i][local_max[0]]))

    for j in xrange(0, len(local_min)):
        max_j = j + max_min
        if max_j >= len(local_max):
            break

        if j < len(local_min) - 1:
            burst_end = min(local_min[j + 1], 2 *
                            local_max[max_j] - local_min[j] + 30)
        else:
            burst_end = min(n-1, 2 * local_max[max_j] - local_min[j] + 30)
        # if j < len(local_min) - 1:
        #    burst_end = local_min[j+1]
        # else:
        #    burst_end = n

        if check_up_slope(series[i], local_min[j], burst_end, local_max[max_j], st_p) or check_down_slope(series[i], local_min[j], burst_end, local_max[max_j], st_p):
            burst.append((local_min[j], burst_end, local_max[
                max_j], series[i][local_max[max_j]]))

    j = 0
    new_burst = []
    while j < len(burst):
        # if first burst end equals second burst start, try to combine
        start, end, top = burst[j][0], burst[j][1], burst[j][2]
        while True:
            if j >= len(burst) - 1:
                break

            check_sum = 0
            if(end == burst[j+1][0]):
                check_sum = combine_bursts(series[i], top, burst[j+1][2], start, end, burst[j+1][1])

            if check_sum == 0:
                break

            if check_sum % 2 == 1:
                end = burst[j+1][1]
            if check_sum / 2 == 1:
                top = burst[j+1][2]
            j += 1

        new_burst.append((start, end, top, series[i][top]))
        j += 1

    burst_writer.writerow(new_burst)

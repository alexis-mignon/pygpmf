from collections import namedtuple
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

from . import parse


GPSData = namedtuple("GPSData",
                     [
                         "description", 
                         "timestamp", # yyyy-mm-dd HH:MM:SS.FFF
                         "microseconds", # microseconds since beginning of recording
                         "samples_delivered", # number of samples delivered since beginning of recording
                         "precision", # gps precision (under 500 is good)
                         "fix", # indicates if the go pro orientation is fixed
                         "latitude", # latitude [deg]
                         "longitude", # longitude [deg]
                         "altitude", # altitude (z) [m]
                         "speed_2d", # speed in 2d (x, y) [m/s]
                         "speed_3d", # speed in 3d (x, y, z) [m/s]
                         "units", # units of various quantities
                         "npoints", # number of gps points
                     ])


def extract_gps_blocks(stream):
    """ Extract GPS data blocks from binary stream

    This is a generator on lists `KVLItem` objects. In
    the GPMF stream, GPS data comes into blocks of several
    different data items. For each of these blocks we return a list.

    Parameters
    ----------
    stream: bytes
        The raw GPMF binary stream

    Returns
    -------
    gps_items_generator: generator
        Generator of lists of `KVLItem` objects
    """
    for s in parse.filter_klv(stream, "STRM"):
        content = []
        is_gps = False
        for elt in s.value:
            content.append(elt)
            if elt.key == "GPS5":
                is_gps = True
        if is_gps:
            # print(content)
            yield content


def parse_gps_block(gps_block):
    """Turn GPS data blocks into `GPSData` objects

    Parameters
    ----------
    gps_block: list of KVLItem
        A list of KVLItem corresponding to a GPS data block.

    Returns
    -------
    gps_data: GPSData
        A GPSData object holding the GPS information of a block.
    """
    block_dict = {
        s.key: s for s in gps_block
    }

    gps_data = block_dict["GPS5"].value * 1.0 / block_dict["SCAL"].value

    latitude, longitude, altitude, speed_2d, speed_3d = gps_data.T

    return GPSData(
        description=block_dict["STNM"].value,
        timestamp=block_dict["GPSU"].value,
        microseconds=block_dict["STMP"].value,
        samples_delivered=block_dict['TSMP'].value,
        precision=block_dict["GPSP"].value / 100.,
        fix=block_dict["GPSF"].value,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        speed_2d=speed_2d,
        speed_3d=speed_3d,
        units=block_dict["UNIT"].value,
        npoints=len(gps_data)
    )


FIX_TYPE = {
    0: "none",
    2: "2d",
    3: "3d"
}

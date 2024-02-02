from collections import namedtuple
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import gpxpy
from . import parse
import numpy as np


GPSData = namedtuple("GPSData",
                     [
                         "description",
                         "timestamp",
                         "precision",
                         "fix",
                         "latitude",
                         "longitude",
                         "altitude",
                         "speed_2d",
                         "speed_3d",
                         "units",
                         "npoints"
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

    gps5_array = block_dict["GPS5"].value
    scal_array = block_dict["SCAL"].value
    if gps5_array.size > 0 and scal_array.size > 0:
        gps_data = gps5_array * 1.0 / scal_array
    else:
        gps_data = None

    if gps_data is not None:
        latitude, longitude, altitude, speed_2d, speed_3d = gps_data.T

        return GPSData(
            description=block_dict["STNM"].value,
            timestamp=block_dict["GPSU"].value,
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
    else:
        return None


FIX_TYPE = {
    0: "none",
    2: "2d",
    3: "3d"
}


def _make_speed_extensions(gps_data, i = None):
    speed_2d = ET.Element("speed_2d")
    value = ET.SubElement(speed_2d, "value")
    value.text = ("%g" % gps_data.speed_2d) if i is None else ("%g" % gps_data.speed_2d[i])
    unit = ET.SubElement(speed_2d, "unit")
    unit.text = "m/s"

    speed_3d = ET.Element("speed_3d")
    value = ET.SubElement(speed_3d, "value")
    value.text = ("%g" % gps_data.speed_3d)  if i is None else ("%g" % gps_data.speed_3d[i])
    unit = ET.SubElement(speed_3d, "unit")
    unit.text = "m/s"

    return [speed_2d, speed_3d]


def make_pgx_segment(gps_blocks, first_only=False, speeds_as_extensions=True):
    """Convert a list of GPSData objects into a GPX track segment.

    Parameters
    ----------
    gps_blocks: list of GPSData
        A list of GPSData objects
    first_only: bool, optional (default=False)
        If True use only the first GPS entry of each data block.
    speeds_as_extensions: bool, optional (default=True)
        If True, include 2d and 3d speed values as exentensions of
        the GPX trackpoints. This is especially useful when saving
        to GPX 1.1 format.

    Returns
    -------
    gpx_segment: gpxpy.gpx.GPXTrackSegment
        A gpx track segment.
    """

    track_segment = gpxpy.gpx.GPXTrackSegment()
    dt = timedelta(seconds=1.0 / 18.)

    for gps_data in gps_blocks:
        if gps_data is not None:
            time = datetime.strptime(gps_data.timestamp, "%Y-%m-%d %H:%M:%S.%f")
            # Reference says the frequency is about 18 Hz and other GPS data about 1Hz

            if((type(gps_data.latitude) != type([])) and (type(gps_data.longitude) != type([]))):
                tp = gpxpy.gpx.GPXTrackPoint(
                    latitude=gps_data.latitude,
                    longitude=gps_data.longitude,
                    elevation=gps_data.altitude,
                    speed=gps_data.speed_3d,
                    position_dilution=gps_data.precision,
                    time=time,
                    symbol="Square",
                )

                tp.type_of_gpx_fix = FIX_TYPE[gps_data.fix]

                if speeds_as_extensions:

                    for e in _make_speed_extensions(gps_data, None):
                        tp.extensions.append(e)

                track_segment.points.append(tp)
                continue

            # stop = 1 if first_only else gps_data.npoints
            stop = min([len(gps_data.latitude),len(gps_data.longitude)])
            for i in range(stop):
                tp = gpxpy.gpx.GPXTrackPoint(
                    latitude=gps_data.latitude[i],
                    longitude=gps_data.longitude[i],
                    elevation=gps_data.altitude[i],
                    speed=gps_data.speed_3d[i],
                    position_dilution=gps_data.precision,
                    time=time + i * dt,
                    symbol="Square",
                )

                tp.type_of_gpx_fix = FIX_TYPE[gps_data.fix]

                if speeds_as_extensions:

                    for e in _make_speed_extensions(gps_data, 0):
                        tp.extensions.append(e)

                track_segment.points.append(tp)

    return track_segment

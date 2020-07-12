from collections import namedtuple
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET

import gpxpy
from . import parse


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
    block_dict = {
        s.key: s for s in gps_block
    }

    gps_data = block_dict["GPS5"].value * 1.0 / block_dict["SCAL"].value

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


FIX_TYPE = {
    0: "none",
    2: "2d",
    3: "3d"
}


def _make_speed_extensions(gps_data, i):
    speed_2d = ET.Element("speed_2d")
    value = ET.SubElement(speed_2d, "value")
    value.text = "%g" % gps_data.speed_2d[i]
    unit = ET.SubElement(speed_2d, "unit")
    unit.text = "m/s"

    speed_3d = ET.Element("speed_3d")
    value = ET.SubElement(speed_3d, "value")
    value.text = "%g" % gps_data.speed_3d[i]
    unit = ET.SubElement(speed_3d, "unit")
    unit.text = "m/s"

    return [speed_2d, speed_3d]


def make_pgx_segment(gps_blocks, first_only=False, speeds_as_extensions=True):

    track_segment = gpxpy.gpx.GPXTrackSegment()
    dt = timedelta(seconds=1.0 / 18.)

    for gps_data in gps_blocks:
        time = datetime.strptime(gps_data.timestamp, "%Y-%m-%d %H:%M:%S.%f")
        # Reference says the frequency is about 18 Hz and other GPS data about 1Hz
        stop = 1 if first_only else gps_data.npoints
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

import os
import sys
import argparse
import json

import numpy
import gpxpy
import matplotlib.pyplot as plt


from .gps import extract_gps_blocks, make_pgx_segment, parse_gps_block
from .parse import filter_klv
from .io import extract_gpmf_stream
from .gps_plot import plot_gps_trace


def parse_args():
    parser = argparse.ArgumentParser()

    # GPS Extract
    subparsers = parser.add_subparsers(dest="command")
    gps_parser = subparsers.add_parser("gps-extract")
    gps_parser.add_argument("file", help="Input File")
    gps_parser.add_argument('-o', '--output-file', default=None)
    gps_parser.add_argument('-d', '--output-directory', default=None)
    gps_parser.add_argument('-f', '--first-only', action="store_true",
                            help="Store only the first GPS entry of a block")
    gps_parser.add_argument("-n", "--no-speed", action="store_true",
                            help="Do not store speed informations as extensions")
    gps_parser.add_argument("-g", "--gpx-version", choices=["1.0", "1.1"], default="1.1",
                            help="The GPX version to use (default=1.0)")

    # GPS First Position
    gps_first_parser = subparsers.add_parser("gps-first")
    gps_first_parser.add_argument("file")

    # GPS Plot
    gps_plot_parser = subparsers.add_parser("gps-plot")
    gps_plot_parser.add_argument("file")
    gps_plot_parser.add_argument('-o', '--output-file', default=None)
    gps_plot_parser.add_argument('-d', '--output-directory', default=None)
    gps_plot_parser.add_argument('-f', '--first-only', action="store_true",
                            help="Plot only the first GPS entry of a block")
    return parser.parse_args()


def command_gpx_extract(args):
    infile = args.file

    if args.output_file is None:
        output_path = os.path.splitext(infile)[0] + ".gpx"
        if args.output_directory is not None:
            basename = os.path.basename(output_path)
            output_path = os.path.join(args.output_directory, basename)
    else:
        output_path = args.output_file

    gpmf_stream = extract_gpmf_stream(infile)
    gps_blocks = extract_gps_blocks(gpmf_stream)
    gps_data_blocks = map(parse_gps_block, gps_blocks)

    gpx = gpxpy.gpx.GPX()
    gpx_track = gpxpy.gpx.GPXTrack()
    gpx_segment = make_pgx_segment(gps_data_blocks)
    gpx.tracks.append(gpx_track)
    gpx_track.segments.append(gpx_segment)

    with open(output_path, "w") as out_file:
        out_file.write(gpx.to_xml(version=args.gpx_version))


def command_gps_first(args):
    infile = args.file

    gpmf_stream = extract_gpmf_stream(infile)
    gps_block = None

    for stream_item in filter_klv(gpmf_stream, "STRM"):
        is_gps = False
        content = []
        for klv_item in stream_item.value:
            content.append(klv_item)
            if klv_item.key == "GPS5":
                is_gps = True
        if is_gps:
            gps_block = content
            break

    if gps_block is not None:
        gps_data = parse_gps_block(gps_block)

        info = {
            "latitude": gps_data.latitude[0],
            "longitude": gps_data.longitude[0],
            "speed": gps_data.speed_3d[0],
            "timestamp": gps_data.timestamp
        }

        print(json.dumps(info))
    else:
        print("No GPS information found", file=sys.stderr)


def command_gps_plot(args):
    infile = args.file

    if args.output_file is None:
        output_path = os.path.splitext(infile)[0] + ".png"
        if args.output_directory is not None:
            basename = os.path.basename(output_path)
            output_path = os.path.join(args.output_directory, basename)
    else:
        output_path = args.output_file

    gpmf_stream = extract_gpmf_stream(infile)
    gps_blocks = extract_gps_blocks(gpmf_stream)
    gps_data_blocks = map(parse_gps_block, gps_blocks)

    if args.first_only:
        latlon = numpy.array([[b.latitude[0], b.longitude[0]] for b in gps_data_blocks])
    else:
        latlon = numpy.vstack([
            numpy.vstack([b.latitude, b.longitude]).T for b in gps_data_blocks
        ])

    plot_gps_trace(latlon)
    plt.tight_layout()
    plt.savefig(output_path)


COMMANDS = {
    "gpx-extract": command_gpx_extract,
    "gps-first": command_gps_first,
    "gps-plot": command_gps_plot
}


def main():
    args = parse_args()
    COMMANDS[args.command](args)


if __name__ == "__main__":
    main()

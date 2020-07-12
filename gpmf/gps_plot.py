import matplotlib.pyplot as plt
import geopandas as gpd
import contextily as ctx
import numpy
import pandas


from .gps import extract_gps_blocks, parse_gps_block


LATLON = "EPSG:4326"
LAMBERT93 = "EPSG:2154"


def to_dataframe(gps_data_blocks):
    """Convert a sequence of GPSData into pandas dataframe.

    Parameters
    ----------
    gps_data_blocks: seq of GPSData
        A sequence of GPSData objects
    Returns
    -------
    df_gps: pandas.DataFrame
        The output dataframe
    """
    df_blocks = []
    for i, block in enumerate(gps_data_blocks):
        df_block = pandas.DataFrame()
        df_block["latitude"] = block.latitude
        df_block["longitude"] = block.longitude
        df_block["altitude"] = block.altitude
        df_block["time"] = block.timestamp
        df_block["speed_2d"] = block.speed_2d
        df_block["speed_3d"] = block.speed_3d
        df_block["precision"] = block.precision
        df_block["fix"] = block.fix
        df_block["block_id"] = i
        df_blocks.append(df_block)

    return pandas.concat(df_blocks)


def filter_outliers(x):
    """Filter outliers based on 0.01 and 0.99 quantiles"""
    q01, q50, q99 = numpy.quantile(x, q=[0.01, 0.5, 0.99])
    return (q50 - (1.1 * (q50 - q01)) < x) & (x < q50 + (1.1 * (q99 - q50)))


def plot_gps_trace(latlon,
                   min_tile_size=10,
                   map_provider=None,
                   zoom=12,
                   figsize=(10, 10),
                   proj_crs=LAMBERT93,
                   color="tab:red"):
    """ Plot a (lat, lon) coordinates on a Map

    Parameters
    ----------
    latlon: numpy.ndarray
        Array of (latitude, longitude) coordinates
    min_tile_size: int, optional (default=10)
        Minimum size of the map in km
    map_provider: dict
        Dictionnary describing a map provider as given by `contextly.providers`. If None
        `contextily.providers.GeoportailFrance["maps"]` is used.
    zoom: int, optional (default=12)
        The zoom level used.
    figsize: tuple of int, optional (default=(10, 10))
        The matplotlib figure size
    proj_crs: str or geopandas.CRS object, optional (default="EPSG:2154")
        The projection system used to compute distances on the map. The default value
        corresponds to the Lambert 93 system.
    color: str, optional (default="tab:red")
        The color used to plot the track.
    """
    if map_provider is None:
        map_provider = ctx.providers.GeoportailFrance["maps"]

    min_tile_size *= 1000

    y, x = latlon.T

    mask = filter_outliers(x) & filter_outliers(y)

    df = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy(x[mask], y[mask], crs=LATLON)
    )

    plt.figure(figsize=figsize)
    ax = plt.gca()

    df.to_crs(proj_crs).plot(ax=ax, color=color)

    xmin, xmax = plt.xlim()
    dx = xmax - xmin

    if dx < min_tile_size:
        xc = 0.5 * (xmin + xmax)
        xmin = xc - min_tile_size / 2
        xmax = xc + min_tile_size / 2
        plt.xlim(xmin, xmax)

    ymin, ymax = plt.ylim()
    dy = ymax - ymin

    if dy < min_tile_size:
        yc = 0.5 * (ymin + ymax)
        ymin = yc - min_tile_size / 2
        ymax = yc + min_tile_size / 2
        plt.ylim(ymin, ymax)

    ctx.add_basemap(ax, source=map_provider, zoom=zoom, crs=proj_crs)
    ax.set_axis_off()


def plot_gps_trace_from_stream(stream,
                               first_only=False,
                               min_tile_size=10,
                               map_provider=None,
                               zoom=12,
                               figsize=(10, 10),
                               proj_crs=LAMBERT93,
                               output_path=None,
                               precision_max=3.0,
                               color="tab:red"):
    """ Plot GPS data from a string on a map.

        Parameters
        ----------
        stream: bytes
            The raw GPMF binary stream.
        min_tile_size: int, optional (default=10)
            Minimum size of the map in km
        map_provider: dict
            Dictionnary describing a map provider as given by `contextly.providers`. If None
            `contextily.providers.GeoportailFrance["maps"]` is used.
        zoom: int, optional (default=12)
            The zoom level used.
        figsize: tuple of int, optional (default=(10, 10))
            The matplotlib figure size
        proj_crs: str or geopandas.CRS object, optional (default="EPSG:2154")
            The projection system used to compute distances on the map. The default value
            corresponds to the Lambert 93 system.
        color: str, optional (default="tab:red")
            The color used to plot the track.
    """
    gps_data_blocks = map(parse_gps_block, extract_gps_blocks(stream))

    if first_only:
        latlon = numpy.array([[b.latitude[0], b.longitude[0]]
                              for b in gps_data_blocks
                              if b.precision < precision_max])
    else:
        latlon = numpy.vstack([
            numpy.vstack([b.latitude, b.longitude]).T
            for b in gps_data_blocks
            if b.precision < precision_max
        ])

    plot_gps_trace(latlon, min_tile_size=min_tile_size,
                   map_provider=map_provider,
                   zoom=zoom, figsize=figsize,
                   proj_crs=proj_crs, color=color)
    plt.tight_layout()

    if output_path is not None:
        plt.savefig(output_path)


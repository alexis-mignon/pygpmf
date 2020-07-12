from collections import namedtuple
import types
import struct
import logging
import numpy


logger = logging.getLogger(__name__)

KLVItem = namedtuple("KLVItem", ["key", "length", "value"])
KLVLength = namedtuple("KLVLength", ["type", "size", "repeat"])


def ceil4(x):
    """ Find the closest greater or equal multiple of 4

    Parameters
    ----------
    x: int
        The size

    Returns
    -------
    x_ceil: int
        The closest greater integer which is a multiple of 4.
    """
    return (((x - 1) >> 2) + 1) << 2


num_types = {
    "d": ("float64", "d"),
    "f": ("float32", "f"),
    "b": ("int8", "b"),
    "B": ("uint8", "B"),
    "s": ("int16", "h"),
    "S": ("uint16", "H"),
    "l": ("int32", "i"),
    "L": ("uint32", "I"),
    "j": ("int64", "q"),
    "J": ("uint64", "Q")
}


def parse_payload(x, fourcc, type_str, size, repeat):
    """ Parse the payload

    Parameters
    ----------
    x: byte
        The byte array corresponding to the payload
    fourcc: str
        The fourcc code
    type_str: str
        The type of the value
    size: int
        The size of the value
    repeat: int
        The number of times the value is repeated.

    Returns
    -------
    payload: object
        The parsed payload. the actual type depends on the type_str and the size and repeat values.
    """
    if type_str == "\x00":
        return iter_klv(x)
    else:
        x = x[:size * repeat]
        if type_str == "c":
            if fourcc == "UNIT":
                x = list(numpy.frombuffer(x, dtype="S%i" % size))
                return [s.decode("latin1") for s in x]
            else:
                return x.decode("latin1")

        elif type_str in num_types:
            dtype, stype = num_types[type_str]
            dtype = numpy.dtype(">" + stype)
            a = numpy.frombuffer(x, dtype=dtype)
            type_size = dtype.itemsize
            dim1 = size // type_size

            if a.size == 1:
                a = a[0]
            elif dim1 > 1 and repeat > 1:
                a = a.reshape(repeat, dim1)
            return a
        elif type_str == "U":
            x = x.decode()
            year = "20" + x[:2]
            month = x[2:4]
            day = x[4:6]
            hours = x[6:8]
            mins = x[8:10]
            seconds = x[10:]
            return "%s-%s-%s %s:%s:%s" % (year, month, day, hours, mins, seconds)
        else:
            return x


def iter_klv(x):
    """ Iterate on KLV items.

    Parameters
    ----------
    x: byte
        The byte array corresponding to the stream.

    Returns
    -------
    klv_gen: generator
        A generator of (fourcc, (type_str, size, repeat), payload) tuples.
    """
    start = 0

    while start < len(x):
        head = struct.unpack(">cccccBH", x[start: start + 8])
        fourcc = (b"".join(head[:4])).decode()
        type_str, size, repeat = head[4:]
        type_str = type_str.decode()
        start += 8
        payload_size = ceil4(size * repeat)
        payload = parse_payload(x[start: start + payload_size], fourcc, type_str, size, repeat)
        start += payload_size

        yield KLVItem(fourcc, KLVLength(type_str, size, repeat), payload)


def filter_klv(x, filter_fourcc):
    """Filter only KLV items with chosen fourcc code.

    Parameters
    ----------
    x: byte
        The input stream
    filter_fourcc: list of str
        A list of FourCC codes

    Returns
    -------
    klv_gen: generator
        De-nested generator of (fourcc, (type_str, size, repeat), payload) with only chosen fourcc
    """
    generators = [iter(iter_klv(x))]

    while len(generators) > 0:
        it = generators[-1]
        try:
            (fourcc, (type_str, size, repeat), payload) = next(it)
            if fourcc in filter_fourcc:
                yield KLVItem(fourcc, KLVLength(type_str, size, repeat), payload)
            if type_str == "\x00":
                generators.append(iter(payload))
        except StopIteration:
            generators = generators[:-1]


def _expand_klv(x):
    if isinstance(x, types.GeneratorType):
        return [
            KLVItem(fourcc, type_size_repeat, _expand_klv(payload))
            for fourcc, type_size_repeat, payload
            in x
        ]
    else:
        return x


def expand_klv(x):
    """Expand the klv items

    Convert generators of klv items produced by  `iter_klv` to lists.

    Parameters
    ----------
    x

    Returns
    -------

    """
    return _expand_klv(iter_klv(x))

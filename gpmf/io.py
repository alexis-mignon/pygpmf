import logging

logger = logging.getLogger(__name__)

try:
    import ffmpeg

    def find_gpmf_stream(fname):
        probe = ffmpeg.probe(fname)

        for s in probe["streams"]:
            if s["codec_tag_string"] == "gpmd":
                return s

        raise RuntimeError("Could not find GPS stream")

    def extract_gpmf_stream(fname, verbose=False):
        stream_info = find_gpmf_stream(fname)
        stream_index = stream_info["index"]
        return ffmpeg.input(fname)\
            .output("pipe:", format="rawvideo", map="0:%i" % stream_index, codec="copy")\
            .run(capture_stdout=True, capture_stderr=not verbose)[0]


except ImportError:
    logger.info("The 'ffmpeg' module could not be loaded. The function 'find_gpmf_stream' will not be available.")

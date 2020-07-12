from setuptools import setup, find_packages
import pathlib
from gpmf import __version__

HERE = pathlib.Path(__file__).parent
README = (HERE / "README.md").read_text()

if __name__ == "__main__":
    setup(
        name="gpmf",
        author="Alexis Mignon",
        author_email="alexis.mignon@gmail.com",
        description="A module to read GPMF data embedded in GoPro video files.",
        long_description=README,
        long_description_content_type="text/markdown",
        version=__version__,
        packages=find_packages(),
        install_requires=[
            "numpy", "pandas", "gpxpy",
            "python-ffmpeg", "geopandas",
            "contextily", "descartes"
        ]
    )

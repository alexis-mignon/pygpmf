from setuptools import setup, find_packages
import pathlib
__version__ = "0.1"

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
            "ffmpeg-python", "geopandas",
            "contextily", "descartes"
        ],
        url="https://github.com/alexis-mignon/pygpmf"
    )

"""Ansys Python Manager."""
import os
import sys
import warnings

from appdirs import user_cache_dir

if getattr(sys, "frozen", False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    try:
        _THIS_PATH = sys._MEIPASS
    except:
        # this might occur on a single file install
        os.path.dirname(sys.executable)
else:
    _THIS_PATH = os.path.dirname(os.path.abspath(__file__))

# Read in version programmatically from plain text
# this is done so NSIS can also link to the same version
with open(os.path.join(_THIS_PATH, "VERSION")) as fid:
    __version__ = fid.read()

CACHE_DIR = user_cache_dir("ansys_python_installer")

if not os.path.isdir(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except:
        import tempdir

        warnings.warn(f"Unable create cache at {CACHE_DIR}. Using temporary directory")
        CACHE_DIR = tempdir.gettempdir()


try:
    from ansys.tools.installer.main import open_gui  # place this at end to allow import
except ModuleNotFoundError:  # encountered during install
    pass

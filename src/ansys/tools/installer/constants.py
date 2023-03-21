"""Constants file."""

import logging
import os
import sys

from ansys.tools.installer import __version__

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")

ABOUT_TEXT = f"""<h2>Ansys Python Installer {__version__}</h2>
<p>Created by the PyAnsys Team.</p>
<p>If you have any questions or issues, please open an issue the <a href='https://github.com/pyansys/python-installer-qt-gui/issues'>python-installer-qt-gui Issues</a> page.</p>
<p>Alternatively, you can contact us at <a href='mailto:pyansys.core@ansys.com'>pyansys.core@ansys.com</a>.</p>
<p>Copyright 2023 ANSYS, Inc. All rights reserved.</p>
"""


INSTALL_TEXT = """Choose to use either the standard Python install from <a href='https://www.python.org/'>python.org</a> or <a href='https://github.com/conda-forge/miniforge'>miniforge</a>."""

PYTHON_VERSION_TEXT = """Choose the version of Python to install.

While choosing the latest version of Python is generally recommended, some third-party libraries and applications may not yet be fully compatible with the newest release. Therefore, it is recommended to try the second newest version, as it will still have most of the latest features and improvements while also having broader support among third-party packages."""


if getattr(sys, "frozen", False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    try:
        THIS_PATH = sys._MEIPASS
    except:
        # this might occur on a single file install
        os.path.dirname(sys.executable)
else:
    THIS_PATH = os.path.dirname(os.path.abspath(__file__))


ASSETS_PATH = os.path.join(THIS_PATH, "assets")

ANSYS_VENVS = ".ansys_python_venvs"

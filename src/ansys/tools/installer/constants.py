"""Constants file."""

import logging
import os
import sys

from ansys.tools.installer import __version__

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


ABOUT_TEXT = f"""<h2>Ansys Python Installer {__version__}</h2>
<p>Created by the PyAnsys Team.</p>
<p>If you have any questions or issues, please open an issue in <a href='https://github.com/pyansys/python-installer-qt-gui/issues'>python-installer-qt-gui Issues</a> page.</p>
<p>Alternatively, you can contact us at <a href='mailto:pyansys.core@ansys.com'>pyansys.core@ansys.com</a>.</p>
<p>Your use of this software is governed by the MIT License. In addition, this installer allows you to access and install software that is licensed under separate terms ("Separately Licensed Software"). If you chose to install such Separately Licensed Software, you acknowledge that you are responsible for complying with any associated terms and conditions.</p>
<p>Copyright 2023 ANSYS, Inc. All rights reserved.</p>
"""

PYANSYS_DOCS_TEXT = f"""<h2>PyAnsys Documentation</h2>
<p>Access the documentation for the different PyAnsys projects by selecting your desired project and clicking on the 'Open Website' button.</p>
<p>Users are then redirected to the documentation websites for each of the projects.</p>
<p>Feel free to explore the different PyAnsys initiatives.</p>
"""

ANSYS_VENVS = ".ansys_python_venvs"

INSTALL_TEXT = """Choose to use either the standard Python install from <a href='https://www.python.org/'>python.org</a> or <a href='https://github.com/conda-forge/miniforge'>miniforge</a>."""

PYTHON_VERSION_TEXT = """Choose the version of Python to install.

While choosing the latest version of Python is generally recommended, some third-party libraries and applications may not yet be fully compatible with the newest release. Therefore, it is recommended to try the second newest version, as it will still have most of the latest features and improvements while also having broader support among third-party packages."""


PYTHON_VERSION_SELECTION_FOR_VENV = """Choose the version of Python to use for your virtual environment.

Please select the Python version from the table below to create its respective virtual environment."""

NAME_FOR_VENV = f"""Provide the name for your virtual environment.<br><br>Virtual environments are created under user directory <i>{ANSYS_VENVS}</i>. If the name provided already exists for another virtual environment, it will not be created. Users will receive a warning informing of the situation."""

SELECT_VENV_MANAGE_TAB = """Choose a virtual environment to manage.

It is recommended to use virtual environments for package management and launching options."""

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
ANSYS_FAVICON = os.path.join(ASSETS_PATH, "ansys-favicon.png")

PYANSYS_DOCS_SITES = {
    "PyAnsys": "https://docs.pyansys.com",
    "PyAnsys Developer docs": "https://dev.docs.pyansys.com",
    "PyAnsys-Math": "https://math.docs.pyansys.com",
    "PyAEDT": "https://aedt.docs.pyansys.com",
    "PyDPF-Core": "https://dpf.docs.pyansys.com",
    "PyDPF-Post": "https://post.docs.pyansys.com",
    "PyDPF Composites": "https://composites.dpf.docs.pyansys.com",
    "PyFluent": "https://fluent.docs.pyansys.com",
    "PyFluent-Parametric": "https://parametric.fluent.docs.pyansys.com",
    "PyFluent-Visualization": "https://visualization.fluent.docs.pyansys.com",
    "PyMAPDL": "https://mapdl.docs.pyansys.com",
    "PyMAPDL Reader": "https://reader.docs.pyansys.com/",
    "PyMechanical": "https://mechanical.docs.pyansys.com/",
    "PyMotorCAD": "https://motorcad.docs.pyansys.com/",
    "PyPIM": "https://pypim.docs.pyansys.com/",
    "PyPrimeMesh": "https://prime.docs.pyansys.com/",
    "PySeascape": "https://seascape.docs.pyansys.com/",
    "PySystem Coupling": "https://systemcoupling.docs.pyansys.com/",
    "PyTwin": "https://twin.docs.pyansys.com/",
    "Granta MI BoM Analytics": "https://bomanalytics.grantami.docs.pyansys.com/",
}

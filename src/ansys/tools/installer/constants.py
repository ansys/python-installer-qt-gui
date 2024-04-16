# Copyright (C) 2023 - 2024 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Constants file."""

import logging
import os
import sys

from ansys.tools.path.misc import is_linux

from ansys.tools.installer import __version__

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")

ABOUT_TEXT = f"""<h2>Ansys Python Installer {__version__}</h2>
<p>Created by the PyAnsys Team.</p>
<p>Project build using <a href='https://wiki.qt.io/Qt_for_Python'> PySide6</a> and <a href='https://pyinstaller.org/en/stable/'> PyInstaller</a>.</p>
<p>If you have any questions or issues, please open an issue in <a href='https://github.com/ansys/python-installer-qt-gui/issues'>python-installer-qt-gui Issues</a> page.</p>
<p>Alternatively, you can contact us at <a href='mailto:pyansys.core@ansys.com'>pyansys.core@ansys.com</a>.</p>
<p>Your use of this software is governed by the MIT License. In addition, this installer allows you to access and install software that is licensed under separate terms ("Separately Licensed Software"). If you chose to install such Separately Licensed Software, you acknowledge that you are responsible for complying with any associated terms and conditions.</p>
<p>Copyright 2023 - 2024 ANSYS, Inc. All rights reserved.</p>
"""

UNABLE_TO_RETRIEVE_LATEST_VERSION_TEXT = f"""
<p>Ansys Python Installer cannot verify whether it is up-to-date or not. This might be due to a permissions issue.</p>
<p>Currently installed version is {__version__}.</p>
<p>To check for the latest released version, visit the <a href='https://github.com/ansys/python-installer-qt-gui/releases/latest'> latest release</a> site.</p>
"""

PYANSYS_DOCS_TEXT = f"""<h2>PyAnsys Documentation</h2>
<p>Access the documentation for the different PyAnsys projects by selecting your desired project and clicking on the 'Open Website' button.</p>
<p>Users are then redirected to the documentation websites for each of the projects.</p>
<p>Feel free to explore the different PyAnsys initiatives.</p>
"""

USER_PATH = os.path.expanduser("~")
ANSYS_LINUX_PATH = f".local/ansys"
ANSYS_FULL_LINUX_PATH = f"{USER_PATH}/{ANSYS_LINUX_PATH}"

ANSYS_VENVS = ".ansys_python_venvs"

ANSYS_SUPPORTED_PYTHON_VERSIONS = ["3_7", "3_10"]

INSTALL_TEXT = """Choose to use either the standard Python install from <a href='https://www.python.org/'>python.org</a> or <a href='https://github.com/conda-forge/miniforge'>miniforge</a>."""

PYTHON_VERSION_TEXT = """Choose the version of Python to install.

While choosing the latest version of Python is generally recommended, some third-party libraries and applications may not yet be fully compatible with the newest release. Therefore, it is recommended to try the second newest version, as it will still have most of the latest features and improvements while also having broader support among third-party packages."""

PRE_COMPILED_PYTHON_WARNING = """
<b>NOTE:</b> Only 'Python 3.11' version is readily available. Other Python versions are compiled from source and it takes approximately 2-3 minutes."""

PYTHON_VERSION_SELECTION_FOR_VENV = """Choose the version of Python to use for your virtual environment.

Please select the Python version from the table below to create its respective virtual environment."""

NAME_FOR_VENV = f"""Provide the name for your virtual environment.

<br><br>Virtual environments are created under user directory /<i>{ANSYS_LINUX_PATH + "/" + ANSYS_VENVS if is_linux() else ANSYS_VENVS}</i> by default. To configure the default path, go to File >> Configure (Ctrl + D) and provide your preferred path.

If the name provided already exists for another virtual environment, it will not be created. Users will receive a warning informing of the situation. For more details, refer <a href='https://installer.docs.pyansys.com/version/dev/installer.html#create-python-virtual-environment'>here</a>."""

SELECT_VENV_MANAGE_TAB = f"""Choose a virtual environment to manage.

It is recommended to use virtual environments for package management and launching options. Environments which are available under the user directory /<i>{ANSYS_LINUX_PATH + "/" + ANSYS_VENVS if is_linux() else ANSYS_VENVS}</i> are listed by default. To configure this default directory, refer <a href='https://installer.docs.pyansys.com/version/dev/installer.html#managing-python-environments'>here</a>."""

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
    "PyAdditive": "https://additive.docs.pyansys.com",
    "PyAEDT": "https://aedt.docs.pyansys.com",
    "PyAnsys Geometry": "https://geometry.docs.pyansys.com",
    "PyAnsys Math": "https://math.docs.pyansys.com",
    "PyDPF - Core": "https://dpf.docs.pyansys.com",
    "PyDPF - Post": "https://post.docs.pyansys.com",
    "PyDPF - Composites": "https://composites.dpf.docs.pyansys.com",
    "PyDyna": "https://dyna.docs.pyansys.com",
    "PyDynamicReporting": "https://dynamicreporting.docs.pyansys.com",
    "PyEnSight": "https://ensight.docs.pyansys.com",
    "PyFluent": "https://fluent.docs.pyansys.com",
    "PyFluent - Parametric": "https://parametric.fluent.docs.pyansys.com",
    "PyFluent - Visualization": "https://visualization.fluent.docs.pyansys.com",
    "PyMAPDL": "https://mapdl.docs.pyansys.com",
    "PyMAPDL Reader": "https://reader.docs.pyansys.com/",
    "PyMechanical": "https://mechanical.docs.pyansys.com/",
    "PyMotorCAD": "https://motorcad.docs.pyansys.com/",
    "PyOptislang": "https://optislang.docs.pyansys.com/",
    "PyPIM": "https://pypim.docs.pyansys.com/",
    "PyPrimeMesh": "https://prime.docs.pyansys.com/",
    "PySeascape": "https://seascape.docs.pyansys.com/",
    "PySherlock": "https://sherlock.docs.pyansys.com//",
    "PySystemCoupling": "https://systemcoupling.docs.pyansys.com/",
    "PyTurboGrid": "https://turbogrid.docs.pyansys.com/",
    "PyTwin": "https://twin.docs.pyansys.com/",
    "Granta MI BoM Analytics": "https://bomanalytics.grantami.docs.pyansys.com/",
    "Granta MI RecordLists": "https://recordlists.grantami.docs.pyansys.com/",
    # TOOLS
    "Ansys Tools Path": "https://path.tools.docs.pyansys.com/",
    "Ansys Tools Protobuf Compilation Helper": "https://ansys.github.io/ansys-tools-protoc-helper/",
    "PyAnsys Tools Report": "https://report.tools.docs.pyansys.com/",
    "PyAnsys Tools Versioning": "https://versioning.tools.docs.pyansys.com/",
    "PyAnsys Units": "http://units.docs.pyansys.com/",
}

PYANSYS_LIBS = {
    "PyAnsys-Metapackage": "pyansys",
    "PyAdditive": "ansys-additive-core",
    "PyAEDT": "pyaedt",
    "PyAnsys Geometry": "ansys-geometry-core",
    "PyAnsys Math": "ansys-math-core",
    "PyDPF - Core": "ansys-dpf-core",
    "PyDPF - Post": "ansys-dpf-post",
    "PyDPF - Composites": "ansys-dpf-composites",
    "PyDyna": "ansys-dyna-core",
    "PyDynamicReporting": "ansys-dynamicreporting-core",
    "PyEnSight": "ansys-pyensight-core",
    "PyFluent": "ansys-fluent-core",
    "PyFluent - Parametric": "ansys-fluent-parametric",
    "PyFluent - Visualization": "ansys-fluent-visualization",
    "PyMAPDL": "ansys-mapdl-core",
    "PyMAPDL Reader": "ansys-mapdl-reader",
    "PyMechanical": "ansys-mechanical-core",
    "PyMotorCAD": "ansys-motorcad-core",
    "PyOptislang": "ansys-optislang-core",
    "PyPIM": "ansys-platform-instancemanagement",
    "PyPrimeMesh": "ansys-meshing-prime",
    "PySeascape": "ansys-seascape",
    "PySherlock": "ansys-sherlock-core",
    "PySystemCoupling": "ansys-systemcoupling-core",
    "PyTurboGrid": "ansys-turbogrid-core",
    "PyTwin": "pytwin",
    "Granta MI BoM Analytics": "ansys-grantami-bomanalytics",
    "Granta MI RecordLists": "ansys-grantami-recordlists",
    "Shared Components": "ansys-openapi-common",
    # TOOLS
    "Ansys Tools Path": "ansys-tools-path",
    "Ansys Tools Protobuf Compilation Helper": "ansys-tools-protoc-helper",
    "PyAnsys Tools Report": "pyansys-tools-report",
    "PyAnsys Tools Versioning": "pyansys-tools-versioning",
    "PyAnsys Units": "ansys-units",
}

VENV_DEFAULT_PATH = "venv_default_path"
VENV_SEARCH_PATH = "venv_search_path"


###############################################################################
# Python versions
###############################################################################
#
# Do not modify below this section
#

VANILLA_PYTHON_VERSIONS = {
    "Python 3.8": "3.8.10",
    "Python 3.9": "3.9.13",
    "Python 3.10": "3.10.11",
    "Python 3.11": "3.11.6",
    "Python 3.12": "3.12.0",
}

CONDA_PYTHON_VERSION = "23.1.0-4"

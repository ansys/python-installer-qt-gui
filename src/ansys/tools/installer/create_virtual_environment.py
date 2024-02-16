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

"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
from pathlib import Path
import subprocess

from PySide6 import QtCore, QtGui, QtWidgets

from ansys.tools.installer.constants import (
    ANSYS_FAVICON,
    ANSYS_VENVS,
    NAME_FOR_VENV,
    PYTHON_VERSION_SELECTION_FOR_VENV,
)
from ansys.tools.installer.installed_table import DataTable
from ansys.tools.installer.linux_functions import (
    ansys_linux_path,
    create_venv_conda,
    create_venv_linux,
    is_linux_os,
)

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.Type.WindowActivate, QtCore.QEvent.Type.Show]

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class CreateVenvTab(QtWidgets.QWidget):
    """Manage Virtual Environment w.r.t Python versions tab."""

    def __init__(self, parent):
        """Initialize this tab."""
        super().__init__()
        self._parent = parent
        self.venv_table = parent.installed_table_tab.venv_table
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # QIcon object from an image file
        self.app_icon = QtGui.QIcon(ANSYS_FAVICON)

        # Group 1: Select Python version for virtual environment
        python_version_box = QtWidgets.QGroupBox("Select Python version")
        python_version_box_layout = QtWidgets.QVBoxLayout()
        python_version_box_layout.setContentsMargins(10, 20, 10, 20)
        python_version_box.setLayout(python_version_box_layout)

        # ---> Add text for selecting Python version
        python_version_box_text = QtWidgets.QLabel()
        python_version_box_text.setText(PYTHON_VERSION_SELECTION_FOR_VENV)
        python_version_box_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        python_version_box_text.setWordWrap(True)
        python_version_box_layout.addWidget(python_version_box_text)

        # ---> Include table with available Python installations
        self.table = DataTable(installed_python=True, installed_forge=True)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        python_version_box_layout.addWidget(self.table)

        # Group 2: Provide name for virtual environment
        venv_name_box = QtWidgets.QGroupBox("Virtual environment name")
        venv_name_box_layout = QtWidgets.QVBoxLayout()
        venv_name_box_layout.setContentsMargins(10, 20, 10, 20)
        venv_name_box.setLayout(venv_name_box_layout)

        # ---> Add text for virtual environment name
        venv_name_box_text = QtWidgets.QLabel()
        venv_name_box_text.setText(NAME_FOR_VENV)
        venv_name_box_text.setTextFormat(QtCore.Qt.TextFormat.RichText)
        venv_name_box_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        venv_name_box_text.setWordWrap(True)
        venv_name_box_layout.addWidget(venv_name_box_text)

        # ---> Add box for virtual environment name insertion
        self.venv_name = QtWidgets.QLineEdit()
        self.venv_name.setPlaceholderText("Enter virtual environment name")
        venv_name_box_layout.addWidget(self.venv_name)

        # END: Create virtual environment button
        create_env_btn = QtWidgets.QPushButton("Create")
        create_env_btn.clicked.connect(self.create_venv)

        # Finally, add all the previous widgets to the global layout
        layout.addWidget(python_version_box)
        layout.addWidget(venv_name_box)
        layout.addWidget(create_env_btn)

        # And ensure the table is always in focus
        self.installEventFilter(self)

    def create_venv(self):
        """Create virtual environment at selected directory."""
        user_home = ansys_linux_path if is_linux_os() else os.path.expanduser("~")
        venv_dir = os.path.join(user_home, ANSYS_VENVS, self.venv_name.text())
        if self.venv_name.text() == "":
            self.failed_to_create_dialog(case_1=True)
        elif os.path.exists(venv_dir):
            self.failed_to_create_dialog(case_2=True)
        else:
            Path(venv_dir).mkdir(parents=True, exist_ok=True)
            try:
                self.cmd_create_venv(venv_dir)
            except:
                self.failed_to_create_dialog()

            self.update_table()
            self.venv_success_dialog()

    def venv_success_dialog(self):
        """Dialog appear for successful creation of virtual environment."""
        msg = QtWidgets.QMessageBox()
        msg.setText("Information: Virtual environment successfully created!")
        msg.setWindowTitle("Information")
        msg.setIcon(msg.Icon.Information)
        msg.setWindowIcon(self.app_icon)
        msg.exec_()

    def failed_to_create_dialog(self, case_1=False, case_2=False):
        """Dialogs for if environment gets failed to create."""
        if case_1:
            # Case 1: check for name of environment
            msg = QtWidgets.QMessageBox()
            msg.setText("Warning: Failed to create virtual environment!")
            msg.setInformativeText(
                "Enter a valid name for virtual environment creation."
            )
            msg.setWindowTitle("Warning")
            msg.setIcon(msg.Icon.Warning)
            msg.setWindowIcon(self.app_icon)
            msg.exec_()

        elif case_2:
            # Case 2: if environment already exists
            msg = QtWidgets.QMessageBox()
            msg.setText("Warning: Failed to create virtual environment!")
            msg.setInformativeText(
                "Virtual environment already exists. Please enter a different virtual environment name."
            )
            msg.setWindowTitle("Warning")
            msg.setIcon(msg.Icon.Warning)
            msg.setWindowIcon(self.app_icon)
            msg.exec_()
        else:
            # In case of critical error
            msg = QtWidgets.QMessageBox()
            msg.setText("Error: Failed to create virtual environment!")
            msg.setInformativeText("There might be some issue with application.")
            msg.setWindowTitle("Error")
            msg.setIcon(msg.Icon.Critical)
            msg.setWindowIcon(self.app_icon)
            msg.exec_()

    def update_table(self):
        """Update the Python version table."""
        self.table.update()
        self.venv_table.update()

    def eventFilter(self, source, event):
        """Filter events and ensure that the table always remains in focus."""
        if event.type() in ALLOWED_FOCUS_EVENTS and source is self:
            self.table.setFocus()
        return super().eventFilter(source, event)

    def cmd_create_venv(self, venv_dir):
        """Create a virtual environment in a new command prompt.

        Parameters
        ----------
        venv_dir : str
            The location for the virtual environment.
        """
        py_path = self.table.active_path
        user_profile = os.path.expanduser("~")
        LOG.debug(f"Requesting creation of {venv_dir}")
        if "Python" in self.table.active_version:
            if is_linux_os():
                create_venv_linux(venv_dir, py_path)
            else:
                scripts_path = os.path.join(py_path, "Scripts")
                new_path = f"{py_path};{scripts_path};%PATH%"
                subprocess.call(
                    f'start /w /min cmd /K "set PATH={new_path} && python -m venv {venv_dir} && exit"',
                    shell=True,
                    cwd=user_profile,
                )
        else:
            if is_linux_os():
                create_venv_conda(venv_dir, py_path)
            else:
                subprocess.call(
                    f'start /w /min cmd /K "{py_path}\\Scripts\\activate.bat && conda create --prefix {venv_dir} python -y && exit"',
                    shell=True,
                    cwd=user_profile,
                )

"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
from pathlib import Path
import subprocess

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt

from ansys.tools.installer.constants import ANSYS_VENVS, ASSETS_PATH
from ansys.tools.installer.installed_table import DataTable

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.WindowActivate, QtCore.QEvent.Show]

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
        self.app_icon = QtGui.QIcon(os.path.join(ASSETS_PATH, "ansys-favicon.png"))

        # Create Virtual Environment
        venv_note_text = f"<b>NOTE:</b>  Virtual environments are created under user directory <i>'{ANSYS_VENVS}'</i>.\
            \nPlease select the python version from <i><b>Available Python Installations</b></i> table to create\
            \nrespective virtual environment. Currently Conda Forge Versions are not supported. \n"

        file_browse_title = QtWidgets.QLabel()
        file_browse_title.setText(venv_note_text)
        file_browse_title.setAlignment(Qt.AlignCenter)
        file_browse_title.setWordWrap(True)
        file_browse_title.setContentsMargins(0, 10, 0, 0)
        font = file_browse_title.font()
        file_browse_title.setFont(font)

        self.venv_name = QtWidgets.QLineEdit()
        self.venv_name.setPlaceholderText("Enter virtual environment name")

        create_env_btn = QtWidgets.QPushButton("Create Virtual Environments")
        create_env_btn.clicked.connect(self.create_venv)

        layout.addWidget(file_browse_title)
        layout.addWidget(self.venv_name)
        layout.addWidget(create_env_btn)

        # Form
        form_title = QtWidgets.QLabel("Available Python Installations")
        form_title.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(form_title)

        # Python Version, Forge Version Table
        self.table = DataTable(installed_python=True, installed_forge=True)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        layout.addWidget(self.table)

        # Group 1: Installation type
        installation_type_box = QtWidgets.QGroupBox("Installation Type")
        installation_type_box_layout = QtWidgets.QVBoxLayout()
        installation_type_box_layout.setContentsMargins(10, 20, 10, 20)
        installation_type_box.setLayout(installation_type_box_layout)

        # ensure the table is always in focus
        self.installEventFilter(self)

    def create_venv(self):
        """Create virtual environment at selected directory."""
        user_directory = os.path.expanduser("~")
        venv_dir = ANSYS_VENVS
        user_venv_dir = f"{user_directory}/{venv_dir}/{self.venv_name.text()}"
        isExist = os.path.exists(user_venv_dir)

        if self.venv_name.text() == "":
            self.failed_to_create_dialog(case_1=True)
        elif isExist:
            self.failed_to_create_dialog(case_2=True)
        else:
            Path(f"{user_directory}/{venv_dir}/{self.venv_name.text()}").mkdir(
                parents=True, exist_ok=True
            )
            user_venv_dir = f"{user_directory}/{venv_dir}/{self.venv_name.text()}"
            cmd = f'python -m venv "{user_venv_dir}"'
            self.launch_cmd(cmd, minimized_window=True, exit_cmd="^& exit")
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

    def launch_cmd(self, extra="", minimized_window=False, exit_cmd=""):
        """Run a command in a new command prompt.

        Parameters
        ----------
        extra : str, default: ""
            Any additional command(s).
        minimized_window : bool, default: False
            Whether the window should run minimized or not.
        """
        py_path = self.table.active_path
        user_profile = os.path.expanduser("~")
        min_win = "/w /min" if minimized_window else ""
        if "Python" in self.table.active_version:
            scripts_path = os.path.join(py_path, "Scripts")
            new_path = f"{py_path};{scripts_path};%PATH%"

            if extra:
                cmd = f"& {extra} {exit_cmd}"
            else:
                cmd = f"& echo Python set to {py_path}"

            subprocess.call(
                f'start {min_win} cmd /K "set PATH={new_path};{cmd}"{exit_cmd}',
                shell=True,
                cwd=user_profile,
            )
        else:  # probably conda
            if extra:
                # Replace the pip install command for conda
                extra = extra.replace("pip", "conda")
                cmd = f"& {extra} {exit_cmd}"
            else:
                cmd = f"& echo Activating conda forge at path {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{py_path}\\Scripts\\activate.bat {py_path}&cd %userprofile%{cmd}"{exit_cmd}',
                shell=True,
                cwd=user_profile,
            )

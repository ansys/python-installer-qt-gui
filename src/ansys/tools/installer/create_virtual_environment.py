"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
from pathlib import Path
import subprocess

from PySide6 import QtCore, QtGui, QtWidgets

from ansys.tools.installer.constants import ASSETS_PATH
from ansys.tools.installer.installed_table import DataTable, InstalledTab

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.WindowActivate, QtCore.QEvent.Show]

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class CreateVenvTab(QtWidgets.QWidget):
    """Manage Virtual Environment w.r.t Python versions tab."""

    def __init__(self, parent):
        """Initialize this tab."""
        super().__init__()
        self._parent = parent
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # QIcon object from an image file
        self.app_icon = QtGui.QIcon(os.path.join(ASSETS_PATH, "ansys-favicon.png"))

        # Create Virtual Environment
        file_browse_title = QtWidgets.QLabel(
            "NOTE: Virtual environments are created under user directory .ansys_python_venv.\
            \nPlease select the python version from above table to create respective virtual environment.\
            \nCurrently Conda Forge Versions are not supported. \n"
        )
        file_browse_title.setContentsMargins(0, 10, 0, 0)

        self.venv_name = QtWidgets.QLineEdit()
        self.caption = "Enter virtual environment name here!"
        self.venv_name.setText(self.caption)

        create_env_btn = QtWidgets.QPushButton("Create Virtual Environments")
        create_env_btn.clicked.connect(self.create_venv)
        create_env_btn.setStyleSheet("background-color: #ffb71b;")

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
        venv_dir = ".ansys_python_venv"
        user_venv_dir = f"{user_directory}/{venv_dir}/{self.venv_name.text()}"
        isExist = os.path.exists(user_venv_dir)

        if isExist:
            self.failed_to_create_dialog(case_1=True)
        elif self.venv_name.text() == "" or self.venv_name.text() == self.caption:
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
            # Case 1: if environment already exists or blank name
            msg = QtWidgets.QMessageBox()
            msg.setText("Warning: Failed to create virtual environment!")
            msg.setInformativeText(
                "Either environment is already exists. Or Please enter valid environment name."
            )
            msg.setWindowTitle("Warning")
            msg.setIcon(msg.Icon.Warning)
            msg.setWindowIcon(self.app_icon)
            msg.exec_()
        elif case_2:
            # Case 1: check for name of environment
            msg = QtWidgets.QMessageBox()
            msg.setText("Warning: Failed to create virtual environment!")
            msg.setInformativeText(
                "Enter a valid name for virtual environment to create."
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
        InstalledTab.VENV_TABLE.update()

    def eventFilter(self, source, event):
        """Filter events and ensure that the table always remains in focus."""
        if event.type() in ALLOWED_FOCUS_EVENTS and source is self:
            self.table.setFocus()
        return super().eventFilter(source, event)

    def launch_spyder(self):
        """Launch spyder IDE."""
        # handle errors
        error_msg = "pip install spyder && spyder || echo Failed to launch. Try reinstalling spyder with pip install spyder --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(f"spyder || {error_msg}")

    def launch_jupyterlab(self):
        """Launch Jupyterlab."""
        # handle errors
        error_msg = "pip install jupyterlab && python -m jupyter lab || echo Failed to launch. Try reinstalling jupyterlab with pip install jupyterlab --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(f"python -m jupyter lab || {error_msg}")

    def launch_jupyter_notebook(self):
        """Launch Jupyter Notebook."""
        # handle errors
        error_msg = "pip install jupyter && python -m jupyter notebook || echo Failed to launch. Try reinstalling jupyter with pip install jupyter --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(f"python -m jupyter notebook || {error_msg}")

    def install_defaults(self):
        """Install Python default packages."""
        cmd = "pip install numpy pandas scipy scikit-learn matplotlib && timeout 3 && exit || echo Failed to install default Python packages. Try reinstalling it with pip install numpy pandas scipy scikit-learn matplotlib --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(cmd)

    def install_pyansys(self):
        """Install PyAnsys metapackage."""
        cmd = "pip install pyansys^>=2023 && timeout 3 && exit || echo Failed to install PyAnsys metapackage. Try reinstalling it with pip install pyansys^>=2023 --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(cmd)

    def list_packages(self):
        """List installed Python packages."""
        self.launch_cmd("pip list")

    def _update_pck_mnger(self):
        """Update package manager if needed."""
        cmd = ""
        if "Python" in self.table.active_version:
            cmd = "python -m pip install -U pip & exit"
        elif "Conda" in self.table.active_version:
            cmd = "conda update conda & exit"
        self.launch_cmd(cmd, True)

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

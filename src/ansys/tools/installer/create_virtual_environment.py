
"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
import subprocess
import time

from PySide6 import QtCore, QtWidgets

# from ansys.tools.installer.common import threaded
from ansys.tools.installer.find_python import find_all_python, find_miniforge
from ansys.tools.installer.installed_table import PyInstalledTable

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


        # Create Virtual Environment
        file_browse_title = QtWidgets.QLabel('Note: Virtual environments are created under user directory.')
        file_browse_title.setContentsMargins(0, 0, 0, 0)

        # file_browse = QtWidgets.QPushButton('Browse')
        # file_browse.setContentsMargins(0,0,0,1)
        # file_browse.clicked.connect(self.open_dir_dialog)
        self.venv_name = QtWidgets.QLineEdit()
        self.venv_name.setText("Enter virutal environment name here....")
        # self.venv_name.textChanged.connect(self.textchanged)

        create_env_btn = QtWidgets.QPushButton('Create Virtual Environment')
        create_env_btn.clicked.connect(self.create_venv)
        

        layout.addWidget(file_browse_title)
        # layout.addWidget(file_browse)      
        layout.addWidget(self.venv_name)
        layout.addWidget(create_env_btn)
        
        

        # Form
        form_title = QtWidgets.QLabel("Available Python installations")
        form_title.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(form_title)
        

        form = QtWidgets.QWidget()
        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form.setLayout(form_layout)

        # Group 1: Installation type
        installation_type_box = QtWidgets.QGroupBox("Installation Type")
        installation_type_box_layout = QtWidgets.QVBoxLayout()
        installation_type_box_layout.setContentsMargins(10, 20, 10, 20)
        installation_type_box.setLayout(installation_type_box_layout)

        self.table = PyInstalledTable()
        layout.addWidget(self.table)

        # ensure the table is always in focus
        self.installEventFilter(self)


    def create_venv(self):
        """Creates virtual environment at selected directory."""
        import os
        from pathlib import Path
        user_directory = os.path.expanduser( '~' )
        venv_dir = '.ansys_python_venv'        
        
        user_venv_dir = Path(f"{user_directory}/{venv_dir}/{self.venv_name.text()}").mkdir(parents=True, exist_ok=False)

        cmd = f'python venv {user_venv_dir} '

        self.launch_cmd(extra=cmd)      



    def update_table(self):
        """Update the Python version table."""
        self.table.update()

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

    def launch_cmd(self, extra="", minimized_window=False):
        """Run a command in a new command prompt.

        Parameters
        ----------
        extra : str, default: ""
            Any additional command(s).
        minimized_window : bool, default: False
            Whether the window should run minimized or not.
        """
        py_path = self.table.active_path
        min_win = "/w /min" if minimized_window else ""
        if "Python" in self.table.active_version:
            scripts_path = os.path.join(py_path, "Scripts")
            new_path = f"{py_path};{scripts_path};%PATH%"

            if extra:
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Python set to {py_path}"

            subprocess.call(
                f'start {min_win} cmd /K "set PATH={new_path}&cd %userprofile%{cmd}"',
                shell=True,
            )
        else:  # probably conda
            if extra:
                # Replace the pip install command for conda
                extra = extra.replace("pip", "conda")
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Activating conda forge at path {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{py_path}\\Scripts\\activate.bat {py_path}&cd %userprofile%{cmd}"',
                shell=True,
            )

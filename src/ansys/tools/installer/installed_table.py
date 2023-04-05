"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
import subprocess
import time

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox

from ansys.tools.installer.common import get_pkg_versions
from ansys.tools.installer.find_python import (
    find_all_python,
    find_miniforge,
    get_all_python_venv,
)

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.WindowActivate, QtCore.QEvent.Show]
LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class DataTable(QtWidgets.QTableWidget):
    """Common Table of locally installed Python environments/Virtual Environments."""

    signal_update = QtCore.Signal()

    def __init__(
        self,
        parent=None,
        installed_python=False,
        installed_forge=False,
        created_venv=False,
    ):
        """Initialize the table by populating it."""
        super().__init__(1, 1, parent)

        self.installed_python = installed_python
        self.installed_forge = installed_forge
        self.created_venv = created_venv

        self._destroyed = False
        self._locked = True
        self.populate()
        self.signal_update.connect(self.populate)

    def update(self, timeout=1.0):
        """Update this table.

        Respects a lock to ensure no race conditions or multiple calls on the table.

        """
        tstart = time.time()
        while self._locked:
            time.sleep(0.001)
            if time.time() - tstart > timeout:
                return

        self.signal_update.emit()

    def populate(self):
        """Populate the table."""
        self._locked = True
        LOG.debug("Populating the table")
        self.clear()

        if self._destroyed:
            return

        # Check for python & conda forge versions
        if self.installed_python or self.installed_forge:
            python_lst = find_all_python()
            conda_lst = find_miniforge()

            tot = len(python_lst) + len(conda_lst)
            self.setRowCount(tot)
            self.setColumnCount(3)
            self.setHorizontalHeaderLabels(["Version", "Admin", "Path"])
            self.verticalHeader().setVisible(False)
            self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

            row = 0
            for path, (version, admin) in python_lst.items():
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(f"Python {version}"))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
                self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
                row += 1

            for path, (version, admin) in conda_lst.items():
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(f"Conda {version}"))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
                self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
                row += 1
        elif self.created_venv:
            # Check for virtual environments
            venv_lst = get_all_python_venv()
            tot = len(venv_lst)
            if tot == 0:
                venv_lst["None"] = (None, None)
                tot = 1
            self.setRowCount(tot)
            self.setColumnCount(3)
            self.setHorizontalHeaderLabels(["Virtual Environment", "Admin", "Path"])
            self.verticalHeader().setVisible(False)
            self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

            row = 0
            for path, (version, admin) in venv_lst.items():
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(f"{version}"))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
                self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
                row += 1

        self.resizeColumnsToContents()
        self.selectRow(0)
        self.horizontalHeader().setStretchLastSection(True)

        self.destroyed.connect(self.stop)
        self._locked = False

    def stop(self):
        """Flag that this object is gone."""
        self._destroyed = True

    @property
    def active_path(self):
        """Path of the active row."""
        return self.item(self.currentRow(), 2).text()

    @property
    def active_version(self):
        """Version of the active row."""
        return self.item(self.currentRow(), 0).text()


class InstalledTab(QtWidgets.QWidget):
    """Installed Python versions tab."""

    def __init__(self, parent=None):
        """Initialize this tab."""
        super().__init__()
        self._parent = parent

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        form_note_1 = QtWidgets.QLabel(
            "NOTE: Virtual environments are recommended to use with 'Lauching Options' & 'Install' action."
        )
        layout.addWidget(form_note_1)
        font = form_note_1.font()
        font.setItalic(True)
        font.setBold(True)
        form_note_1.setFont(font)

        # Form
        venv_form_title = QtWidgets.QLabel("Available Virtual Environments")
        venv_form_title.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(venv_form_title)

        # Virtual Environment Table
        self.venv_table = DataTable(created_venv=True)
        self.venv_table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        layout.addWidget(self.venv_table)

        launching_options = QtWidgets.QLabel("Launching options")
        launching_options.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(launching_options)

        hbox = QtWidgets.QHBoxLayout()
        layout.addLayout(hbox)
        self.button_launch_cmd = QtWidgets.QPushButton("Launch Console")
        self.button_launch_cmd.clicked.connect(self.launch_cmd)
        hbox.addWidget(self.button_launch_cmd)

        self.button_launch_lab = QtWidgets.QPushButton("Launch Jupyterlab")
        self.button_launch_lab.clicked.connect(self.launch_jupyterlab)
        hbox.addWidget(self.button_launch_lab)

        self.button_launch_notebook = QtWidgets.QPushButton("Launch Jupyter Notebook")
        self.button_launch_notebook.clicked.connect(self.launch_jupyter_notebook)
        hbox.addWidget(self.button_launch_notebook)

        self.button_launch_spyder = QtWidgets.QPushButton("Launch Spyder")
        self.button_launch_spyder.clicked.connect(self.launch_spyder)
        hbox.addWidget(self.button_launch_spyder)

        package_management = QtWidgets.QLabel("Package management")
        package_management.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(package_management)

        hbox_install = QtWidgets.QHBoxLayout()
        layout.addLayout(hbox_install)

        self.button_install_defaults = QtWidgets.QPushButton(
            "Install Python default packages"
        )
        self.button_install_defaults.clicked.connect(self.install_defaults)
        hbox_install.addWidget(self.button_install_defaults)

        self.button_list_packages = QtWidgets.QPushButton("List installed packages")
        self.button_list_packages.clicked.connect(self.list_packages)
        hbox_install.addWidget(self.button_list_packages)

        package_management2 = QtWidgets.QLabel(
            "Package management for PyAnsys Libraries"
        )
        package_management2.setContentsMargins(0, 10, 0, 0)
        layout.addWidget(package_management2)
        hbox_install_pyansys = QtWidgets.QHBoxLayout()
        layout.addLayout(hbox_install_pyansys)

        self.model = QStandardItemModel()
        self.packages_combo = QComboBox()
        self.packages_combo.setModel(self.model)

        self.versions_combo = QComboBox()
        self.versions_combo.setModel(self.model)

        self.button_launch_cmd = QtWidgets.QPushButton("Install")
        self.button_launch_cmd.clicked.connect(self.install_pyansys_packages)

        self.package_pip_dict = {
            "PyAnsys-Metapackage": "pyansys",
            "PyAEDT": "pyaedt",
            "PyDPF-Core": "ansys-dpf-core",
            "PyDPF-Post": "ansys-dpf-post",
            "PyDPF Composites": "ansys-dpf-composites",
            "PyFluent": "ansys-fluent-core",
            "PyFluent-Parametric": "ansys-fluent-parametric",
            "PyFluent-Visualization": "ansys-fluent-visualization",
            "PyMAPDL": "ansys-mapdl-core",
            "PyMAPDL Reader": "ansys-mapdl-reader",
            "PyPIM": "ansys-platform-instancemanagement",
            "PyPrimeMesh": "ansys-meshing-prime",
            "PySeascape": "ansys-seascape",
            "PyTwin": "pytwin",
            "Granta MI BoM Analytics": "ansys-grantami-bomanalytics",
            "Shared Components": "ansys-openapi-common",
        }

        # add data
        data = {}

        for key, value in self.package_pip_dict.items():
            data[key] = get_pkg_versions(value)

        for k, v in data.items():
            package = QStandardItem(k)
            self.model.appendRow(package)
            for value in v:
                version = QStandardItem(value)
                package.appendRow(version)

        self.packages_combo.currentIndexChanged.connect(self.update_package_combo)
        self.update_package_combo(0)

        hbox_install_pyansys.addWidget(self.packages_combo)
        hbox_install_pyansys.addWidget(self.versions_combo)
        hbox_install_pyansys.addWidget(self.button_launch_cmd)

        self.check_box_opt = QtWidgets.QCheckBox(
            "NOT RECOMMENDED: Use of general Python installation"
        )
        self.check_box_opt.setCheckState(QtCore.Qt.CheckState.Unchecked)
        layout.addWidget(self.check_box_opt)
        self.check_box_opt.stateChanged.connect(self.set_chk_box_focus)

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

        # Python Version, Forge Version Table
        self.table = DataTable(installed_python=True, installed_forge=True)
        layout.addWidget(self.table)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)

        # ensure the table is always in focus
        self.installEventFilter(self)

    def update_table(self):
        """Update the Python version table."""
        self.table.update()
        self.venv_table.update()

    def set_chk_box_focus(self, state):
        """Set the focus accordingly depending on check box."""
        self.table.setFocus() if state else self.venv_table.setFocus()

    def is_chk_box_active(self):
        """Get the value of the check box."""
        return (
            True
            if self.check_box_opt.checkState() is QtCore.Qt.CheckState.Checked
            else False
        )

    def eventFilter(self, source, event):
        """Filter events and ensure that the table always remains in focus."""
        if event.type() in ALLOWED_FOCUS_EVENTS and source is self:
            self.set_chk_box_focus(self.is_chk_box_active())
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

    def install_pyansys_packages(self):
        """Install PyAnsys - chosen packages."""
        chosen_pkg = self.packages_combo.currentText()
        chosen_ver = self.versions_combo.currentText()
        cmd = f"pip install {self.package_pip_dict[chosen_pkg]}=={chosen_ver} && timeout 3 && exit || echo Failed to install this PyAnsys Library. Try reinstalling it with pip install {self.package_pip_dict[chosen_pkg]}=={chosen_ver} --force-reinstall"
        self._update_pck_mnger()
        self.launch_cmd(cmd)

    def update_package_combo(self, index):
        """Update the dropdown of available versions based on the package chosen."""
        indx = self.model.index(index, 0, self.packages_combo.rootModelIndex())
        self.versions_combo.setRootModelIndex(indx)
        self.versions_combo.setCurrentIndex(0)

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
        if self.is_chk_box_active():
            py_path = self.table.active_path
        else:
            py_path = self.venv_table.active_path

        min_win = "/w /min" if minimized_window else ""
        if "Python" in self.table.active_version and self.is_chk_box_active():
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
        elif not self.is_chk_box_active():
            # Launch with active virtual environment
            if extra:
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Python set to {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{py_path}\\activate.bat {py_path}&cd %userprofile%{cmd}"',
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

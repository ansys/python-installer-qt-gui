"""Installed Python versions table module for Ansys Python Manager."""

import logging
import os
import subprocess
import time

from PySide6 import QtCore, QtWidgets
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QComboBox

from ansys.tools.installer.common import get_pkg_versions
from ansys.tools.installer.constants import SELECT_VENV_MANAGE_TAB
from ansys.tools.installer.find_python import (
    find_all_python,
    find_miniforge,
    get_all_python_venv,
)

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.Type.WindowActivate, QtCore.QEvent.Type.Show]
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
            self.setHorizontalHeaderLabels(["Virtual environment", "Admin", "Path"])
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

        # Group 1: Available Virtual Environments
        self.available_venv_box = QtWidgets.QGroupBox("Available virtual environments")
        available_venv_box_layout = QtWidgets.QVBoxLayout()
        available_venv_box_layout.setContentsMargins(10, 20, 10, 20)
        self.available_venv_box.setLayout(available_venv_box_layout)

        # --> Add text for available virtual environments
        available_venv_box_text = QtWidgets.QLabel()
        available_venv_box_text.setText(SELECT_VENV_MANAGE_TAB)
        available_venv_box_text.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        available_venv_box_text.setWordWrap(True)
        available_venv_box_layout.addWidget(available_venv_box_text)

        # --> Add the virtual environment table
        self.venv_table = DataTable(created_venv=True)
        self.venv_table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)

        available_venv_box_layout.addWidget(self.venv_table)
        layout.addWidget(self.available_venv_box)

        # EXTRA Group: Available Python installation
        self.available_python_install_box = QtWidgets.QGroupBox(
            "Available base Python versions"
        )
        available_python_install_box_layout = QtWidgets.QVBoxLayout()
        available_python_install_box_layout.setContentsMargins(10, 20, 10, 20)
        self.available_python_install_box.setLayout(available_python_install_box_layout)

        # Python Version, Forge Version Table
        self.table = DataTable(installed_python=True, installed_forge=True)
        self.table.setSelectionMode(QtWidgets.QTableWidget.SingleSelection)
        available_python_install_box_layout.addWidget(self.table)
        layout.addWidget(self.available_python_install_box)

        # Hide it at first
        self.available_python_install_box.hide()

        # EXTRA: Use general Python installations for the above actions
        self.check_box_opt = QtWidgets.QCheckBox(
            "NOT RECOMMENDED: Use base Python versions instead of virtual environments."
        )
        self.check_box_opt.setCheckState(QtCore.Qt.CheckState.Unchecked)
        layout.addWidget(self.check_box_opt)
        self.check_box_opt.stateChanged.connect(self.set_chk_box_focus)
        self.check_box_opt.stateChanged.connect(self.display_ctrl)

        ####### Launching and package management options #######

        # Group 2: Launching Options
        launching_options_box = QtWidgets.QGroupBox("Launching options")
        launching_options_box_layout = QtWidgets.QVBoxLayout()
        launching_options_box_layout.setContentsMargins(10, 20, 10, 20)
        launching_options_box.setLayout(launching_options_box_layout)

        hbox = QtWidgets.QHBoxLayout()
        launching_options_box_layout.addLayout(hbox)
        self.button_launch_cmd = QtWidgets.QPushButton("Launch console")
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

        layout.addWidget(launching_options_box)

        # Group 3: Package Management
        pkg_manage_box = QtWidgets.QGroupBox("General package management")
        pkg_manage_box_layout = QtWidgets.QVBoxLayout()
        pkg_manage_box_layout.setContentsMargins(10, 20, 10, 20)
        pkg_manage_box.setLayout(pkg_manage_box_layout)

        hbox_install = QtWidgets.QHBoxLayout()
        pkg_manage_box_layout.addLayout(hbox_install)

        self.button_install_defaults = QtWidgets.QPushButton(
            "Install Python default packages"
        )
        self.button_install_defaults.clicked.connect(self.install_defaults)
        hbox_install.addWidget(self.button_install_defaults)

        self.button_list_packages = QtWidgets.QPushButton("List installed packages")
        self.button_list_packages.clicked.connect(self.list_packages)
        hbox_install.addWidget(self.button_list_packages)

        layout.addWidget(pkg_manage_box)

        # Group 4: PyAnsys Package Management
        pyansys_pkg_manage_box = QtWidgets.QGroupBox("PyAnsys package management")
        pyansys_pkg_manage_box_layout = QtWidgets.QVBoxLayout()
        pyansys_pkg_manage_box_layout.setContentsMargins(10, 20, 10, 20)
        pyansys_pkg_manage_box.setLayout(pyansys_pkg_manage_box_layout)

        hbox_install_pyansys = QtWidgets.QHBoxLayout()
        pyansys_pkg_manage_box_layout.addLayout(hbox_install_pyansys)

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
        layout.addWidget(pyansys_pkg_manage_box)

        # ensure the table is always in focus
        self.installEventFilter(self)

    def update_table(self):
        """Update the Python version table."""
        self.table.update()
        self.venv_table.update()

    def display_ctrl(self):
        """Set the focus accordingly depending on check box."""
        if self.is_chk_box_active():
            self.available_python_install_box.show()
            self.available_venv_box.hide()
        else:
            self.available_python_install_box.hide()
            self.available_venv_box.show()

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
        min_win = "/w /min" if minimized_window else ""

        # venv_yes    -  True :  virtual environment , False: user chose (checked box) base python installation
        # python_yes  -  True : Python , False : Miniforge/Conda

        if self.is_chk_box_active():
            venv_yes = False
            # when base python installation  is chosen in the table
            py_path = self.table.active_path
            py_version = self.table.active_version
            # chosen_general_base_is_python = True if "Python" in py_version else False

            miniforge_path = "" if "Python" in py_version else py_path
            python_yes = True if miniforge_path == "" else False
        else:
            venv_yes = True
            # when virtual environment is chosen in the table
            py_path = self.venv_table.active_path
            parent_path = os.path.dirname(py_path)  # No Scripts Folder
            # If py_path has a folder called conda-meta . then it is a conda environment
            python_yes = False if "conda-meta" in os.listdir(parent_path) else True
            if python_yes:
                miniforge_path = ""
            else:
                py_path = os.path.dirname(py_path)  # No Scripts Folder
                # If it is a conda environment, then we need to get the path to the miniforge installation
                with open(os.path.join(py_path, "conda-meta", "history"), "r") as f:
                    for line in f:
                        if line.startswith("# cmd:"):
                            line = line.lstrip("# cmd: ")
                            path = line.strip().split("create --prefix")[0]
                            miniforge_path = (
                                path.strip().split("Scripts")[0].rstrip("\\")
                            )
                            break
            python_yes = True if miniforge_path == "" else False
        print("py_path           : ", py_path)
        print("python_yes        : ", python_yes)
        print("venv_yes          : ", venv_yes)
        print("miniforge_path    : ", miniforge_path)

        if python_yes and not venv_yes:
            scripts_path = os.path.join(py_path, "Scripts")
            new_path = f"{py_path};{scripts_path};%PATH%"

            if extra:
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Python set to {py_path}"

            subprocess.call(
                f'start {min_win} cmd /K "set PATH={new_path} & cd %userprofile%{cmd}"',
                shell=True,
            )
        elif python_yes and venv_yes:
            # Launch with active python virtual environment
            if extra:
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Python set to {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{py_path}\\activate.bat {py_path} & cd %userprofile%{cmd}"',
                shell=True,
            )
        elif not python_yes and venv_yes:
            # Launch with active conda virtual environment
            if extra:
                # Replace the pip install command for conda
                extra = extra.replace("pip", "conda")
                extra = extra.replace("conda install", "conda install --yes")
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Activating conda forge at path {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{miniforge_path}\\Scripts\\activate.bat && conda activate {py_path} && conda info & cd %userprofile%{cmd}"',
                shell=True,
            )
        else:
            # not python_yes and not venv_yes
            if extra:
                # Replace the pip install command for conda
                extra = extra.replace("pip", "conda")
                extra = extra.replace("conda update conda", "conda update conda --yes")
                extra = extra.replace("conda install", "conda install --yes")
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Activating conda forge at path {py_path}"
            subprocess.call(
                f'start {min_win} cmd /K "{miniforge_path}\\Scripts\\activate.bat && conda activate {py_path} && conda info & cd %userprofile%{cmd}"',
                shell=True,
            )

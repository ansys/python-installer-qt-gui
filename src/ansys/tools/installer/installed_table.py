import logging
import os
import subprocess

from PySide6 import QtCore, QtWidgets

from ansys.tools.installer.common import threaded
from ansys.tools.installer.find_python import find_all_python, find_miniforge

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.WindowActivate, QtCore.QEvent.Show]

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class PyInstalledTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(1, 1, parent)
        self.populate()

    @threaded
    def populate(self):
        """Populate the table."""
        LOG.debug("Populating the table")
        self.clear()
        installed = find_all_python()
        installed_forge = find_miniforge()
        tot = len(installed[0]) + len(installed[1]) + len(installed_forge)
        self.setRowCount(tot)
        self.setColumnCount(3)

        self.setHorizontalHeaderLabels(["Version", "Admin", "Path"])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        row = 0
        for admin in [True, False]:
            for version, path in installed[admin].items():
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(f"Python v{version}"))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
                self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
                row += 1

        for path, (version, admin) in installed_forge.items():
            self.setItem(row, 0, QtWidgets.QTableWidgetItem(f"Conda {version}"))
            self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
            self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
            row += 1

        self.resizeColumnsToContents()
        self.selectRow(0)
        self.horizontalHeader().setStretchLastSection(True)

    @property
    def active_path(self):
        """Path of the active row."""
        return self.item(self.currentRow(), 2).text()

    @property
    def active_version(self):
        """Version of the active row."""
        return self.item(self.currentRow(), 0).text()


class InstalledTab(QtWidgets.QWidget):
    signal_update = QtCore.Signal()

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        directions_text = QtWidgets.QLabel("Available Python installs")
        layout.addWidget(directions_text)

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

        # Form
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

        # Connect the focusInEvent signal to the on_focus_in method
        self.installEventFilter(self)

        # other connects
        self.signal_update.connect(self.table.populate)

    def update_table(self):
        """Update this tab's table."""
        print("emit")
        self.signal_update.emit()

    def eventFilter(self, source, event):
        if event.type() in ALLOWED_FOCUS_EVENTS and source is self:
            self.table.setFocus()
        return super().eventFilter(source, event)

    def on_focus_in(self, event):
        # Set the focus to the table whenever the widget gains focus
        self.table.setFocus()

    def launch_spyder(self):
        """Launch spyder IDE"""
        # handle errors
        error_msg = "pip install spyder && spyder || echo Failed to launch. Try reinstalling spyder with pip install spyder --force-reinstall"
        self.launch_cmd(f"spyder || {error_msg}")

    def launch_jupyterlab(self):
        """Launch Jupyterlab"""
        # handle errors
        error_msg = "pip install jupyterlab && python -m jupyter lab || echo Failed to launch. Try reinstalling jupyterlab with pip install jupyterlab --force-reinstall"
        self.launch_cmd(f"python -m jupyter lab || {error_msg}")

    def launch_jupyter_notebook(self):
        """Launch Jupyter Notebook"""
        # handle errors
        error_msg = "pip install jupyter && python -m jupyter notebook || echo Failed to launch. Try reinstalling jupyter with pip install jupyter --force-reinstall"
        self.launch_cmd(f"python -m jupyter notebook || {error_msg}")

    def launch_cmd(self, extra=""):
        """"""
        py_path = self.table.active_path
        if "Python" in self.table.active_version:
            scripts_path = os.path.join(py_path, "Scripts")
            new_path = f"{py_path};{scripts_path};%PATH%"

            if extra:
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Python set to {py_path}"

            subprocess.Popen(
                f'start cmd /K "set PATH={new_path}&cd %userprofile%{cmd}"', shell=True
            )
        else:  # probably conda
            if extra:
                # Replace the pip install command for conda
                extra = extra.replace("pip", "conda")
                cmd = f"& {extra}"
            else:
                cmd = f"& echo Activating conda forge at path {py_path}"
            subprocess.Popen(
                f"start cmd /K {py_path}\\Scripts\\activate.bat {py_path}&cd %userprofile%{cmd}", shell=True
            )
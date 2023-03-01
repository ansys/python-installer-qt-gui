import logging
import os
import subprocess

from PySide6 import QtCore, QtWidgets

from ansys.tools.installer.find_python import find_all_python

ALLOWED_FOCUS_EVENTS = [QtCore.QEvent.WindowActivate, QtCore.QEvent.Show]

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


class PyInstalledTable(QtWidgets.QTableWidget):
    def __init__(self, parent=None):
        super().__init__(1, 1, parent)
        self.populate()

    def populate(self):
        """Populate the table."""
        LOG.debug("Populating the table")
        self.clear()
        installed = find_all_python()
        tot = len(installed[0]) + len(installed[1])
        self.setRowCount(tot)
        self.setColumnCount(3)

        self.setHorizontalHeaderLabels(["Version", "Admin", "Path"])
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        row = 0
        for admin in [True, False]:
            for version, path in installed[admin].items():
                self.setItem(row, 0, QtWidgets.QTableWidgetItem(version))
                self.setItem(row, 1, QtWidgets.QTableWidgetItem(str(admin)))
                self.setItem(row, 2, QtWidgets.QTableWidgetItem(path))
                row += 1

        self.resizeColumnsToContents()
        self.selectRow(0)
        self.horizontalHeader().setStretchLastSection(True)

    @property
    def active_path(self):
        return self.item(self.currentRow(), 2).text()


class InstalledTab(QtWidgets.QWidget):
    signal_update = QtCore.Signal()

    def __init__(self, parent):
        super().__init__()
        self._parent = parent
        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        hbox = QtWidgets.QHBoxLayout()
        layout.addLayout(hbox)
        self.button_launch_cmd = QtWidgets.QPushButton("Launch Console")
        self.button_launch_cmd.clicked.connect(self.launch_cmd)
        hbox.addWidget(self.button_launch_cmd)

        self.button_launch_cmd = QtWidgets.QPushButton("Launch Jupyterlab")
        self.button_launch_cmd.clicked.connect(self.launch_jupyterlab)
        hbox.addWidget(self.button_launch_cmd)

        self.button_launch_cmd = QtWidgets.QPushButton("Launch Jupyter Notebook")
        self.button_launch_cmd.clicked.connect(self.launch_jupyter_notebook)
        hbox.addWidget(self.button_launch_cmd)

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

    def update(self):
        """Update this tab's table."""
        self.signal_update.emit()

    def eventFilter(self, source, event):
        if event.type() in ALLOWED_FOCUS_EVENTS and source is self:
            self.table.setFocus()
        return super().eventFilter(source, event)

    def on_focus_in(self, event):
        # Set the focus to the table whenever the widget gains focus
        self.table.setFocus()

    def launch_jupyterlab(self):
        """Launch Jupyterlab"""
        error_msg = "pip install jupyterlab && python -m jupyter lab || echo Failed to launch. Try reinstalling jupyterlab with pip install jupyterlab"
        self.launch_cmd(f"python -m jupyter lab || {error_msg}")

    def launch_jupyter_notebook(self):
        """Launch Jupyter Notebook"""
        error_msg = 'echo Failed to launch. Try reinstalling jupyter with "pip install jupyter --force-reinstall"'
        self.launch_cmd(f"python -m jupyter notebook || {error_msg}")

    def launch_cmd(self, extra=""):
        """"""
        py_path = self.table.active_path
        scripts_path = os.path.join(py_path, "Scripts")
        new_path = f"{py_path};{scripts_path};%PATH%"

        if extra:
            cmd = f"& {extra}"
        else:
            cmd = f"& echo Python set to {py_path}"

        subprocess.Popen(
            f'start cmd /K "set PATH={new_path}&cd %userprofile%{cmd}"', shell=True
        )

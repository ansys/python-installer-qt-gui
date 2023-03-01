"""Main installer window."""
import logging
from math import floor
import os
import sys
from threading import Thread
import urllib.request

from PySide6 import QtCore, QtGui, QtWidgets
import requests

from ansys.tools.installer.common import threaded
from ansys.tools.installer.find_python import find_installed_python, find_miniforge
from ansys.tools.installer.installed_table import InstalledTab
from ansys.tools.installer.installer import install_python
from ansys.tools.installer.progress_bar import ProgressBar

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")

INSTALL_TEXT = """Choose to use either the standard Python install from <a href='https://www.python.org/'>python.org</a> or <a href='https://github.com/conda-forge/miniforge'>miniforge</a>."""

PYTHON_VERSION_TEXT = """Choose the version of Python to install.

While choosing the latest version of Python is generally recommended, some third-party libraries and applications may not yet be fully compatible with the newest release. Therefore, it is recommended to try the second newest version, as it will still have most of the latest features and improvements while also having broader support among third-party packages."""

PACKAGES_INFO_TEXT = """Select the packages to install globally in the Python environment. By default, the "Default" and "PyAnsys" packages are selected, but the user can also choose to install "JupyterLab" or "Spyder (IDE)" by selecting the corresponding check boxes. This allows the user to customize their Python installation to suit their specific needs."""


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


class AnsysPythonInstaller(QtWidgets.QWidget):
    signal_error = QtCore.Signal(str)
    signal_open_pbar = QtCore.Signal(int, str)
    signal_increment_pbar = QtCore.Signal()
    signal_close_pbar = QtCore.Signal()
    signal_set_pbar_value = QtCore.Signal(int)

    def __init__(self, show=True):
        super().__init__()
        self.setWindowTitle("Ansys Python Manager")
        self.setGeometry(50, 50, 500, 900)  # width should auto-update

        self._pbar = None
        self._err_message_box = None

        # Set the global font
        font = QtGui.QFont("Open Sans", -1, QtGui.QFont.Normal, False)
        QtWidgets.QApplication.setFont(font)

        # Create a QIcon object from an image file
        icon = QtGui.QIcon(os.path.join(ASSETS_PATH, "ansys-favicon.png"))
        # Set the application icon
        self.setWindowIcon(icon)

        # Menu
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.setContentsMargins(0, 0, 0, 0)
        menu_widget = QtWidgets.QWidget()
        menu_widget.setLayout(menu_layout)

        self.menu_heading = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(os.path.join(ASSETS_PATH, "pyansys-light-crop.png"))
        self.menu_heading.setPixmap(pixmap)
        menu_layout.addWidget(self.menu_heading)

        # Main content
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_install_python = QtWidgets.QWidget()
        self.tab_widget.addTab(self.tab_install_python, "Install Python")

        # Add tabs to the tab widget
        self._table_tab = InstalledTab(self)
        self.tab_widget.addTab(self._table_tab, "Manage Python Environments")

        # Create the layout for the container
        container_layout = QtWidgets.QVBoxLayout()
        self.tab_install_python.setLayout(container_layout)

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

        installation_type = QtWidgets.QWidget()
        installation_type_layout = QtWidgets.QVBoxLayout()
        installation_type_layout.setContentsMargins(0, 0, 0, 0)
        installation_type.setLayout(installation_type_layout)

        installation_type_text = QtWidgets.QLabel(INSTALL_TEXT)
        installation_type_layout.addWidget(installation_type_text)

        self.installation_type_select = QtWidgets.QComboBox()
        self.installation_type_select.addItem("Standard", "vanilla")
        self.installation_type_select.addItem("Conda (miniforge)", "miniconda")
        installation_type_layout.addWidget(self.installation_type_select)
        self.installation_type_select.currentIndexChanged.connect(
            self._install_type_changed
        )

        installation_type_box_layout.addWidget(installation_type)
        form_layout.addWidget(installation_type_box)

        # Group 2: Python version
        python_version_box = QtWidgets.QGroupBox("Python Version")
        python_version_box_layout = QtWidgets.QVBoxLayout()
        python_version_box_layout.setContentsMargins(10, 20, 10, 20)
        python_version_box.setLayout(python_version_box_layout)

        python_version_text = QtWidgets.QLabel(PYTHON_VERSION_TEXT)
        python_version_text.setWordWrap(True)
        python_version_box_layout.addWidget(python_version_text)

        # Python version
        python_version = QtWidgets.QWidget()
        python_version_layout = QtWidgets.QVBoxLayout()
        python_version_layout.setContentsMargins(0, 0, 0, 0)
        python_version.setLayout(python_version_layout)

        # python_version_title = QtWidgets.QLabel("Python Version")
        # python_version_layout.addWidget(python_version_title)

        # python_version_text = QtWidgets.QLabel("Select one")

        self.python_version_select = QtWidgets.QComboBox()
        self.python_version_select.addItem("Python 3.7", "3.7.9")
        self.python_version_select.addItem("Python 3.8", "3.8.10")
        self.python_version_select.addItem("Python 3.9", "3.9.13")
        self.python_version_select.addItem("Python 3.10", "3.10.10")
        self.python_version_select.addItem("Python 3.11", "3.11.2")

        # Set the default selection to "Python 3.10"
        default_index = self.python_version_select.findText("Python 3.10")
        self.python_version_select.setCurrentIndex(default_index)
        python_version_layout.addWidget(self.python_version_select)

        python_version_box_layout.addWidget(python_version)
        form_layout.addWidget(python_version_box)

        # Group 3: Packages
        packages_box = QtWidgets.QGroupBox("Packages")
        packages_box_layout = QtWidgets.QVBoxLayout()
        packages_box_layout.setContentsMargins(10, 20, 10, 20)
        packages_box.setLayout(packages_box_layout)

        # Packages
        packages = QtWidgets.QWidget()
        packages_layout = QtWidgets.QVBoxLayout()
        # packages_layout.setContentsMargins(0,0,0,0)
        packages.setLayout(packages_layout)

        packages_info_text = QtWidgets.QLabel(PACKAGES_INFO_TEXT)
        packages_info_text.setWordWrap(True)
        packages_layout.addWidget(packages_info_text)

        packages_default = QtWidgets.QCheckBox("Default")
        packages_default.setChecked(True)
        packages_layout.addWidget(packages_default)

        packages_pyansys = QtWidgets.QCheckBox("PyAnsys")
        packages_pyansys.setChecked(True)
        packages_layout.addWidget(packages_pyansys)

        packages_jupyterlab = QtWidgets.QCheckBox("Jupyterlab")
        packages_layout.addWidget(packages_jupyterlab)

        packages_spyder = QtWidgets.QCheckBox("Spyder (IDE)")
        packages_layout.addWidget(packages_spyder)

        packages_box_layout.addWidget(packages)
        form_layout.addWidget(packages_box)

        # ensure content does not get squished
        form_layout.addStretch()

        # Submit button
        self.submit_button = QtWidgets.QPushButton("Install")
        self.submit_button.clicked.connect(self.download_and_install)
        form_layout.addWidget(self.submit_button)

        container_layout.addWidget(form)

        # Add menu and tab widget to main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(menu_widget)
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        # connects
        self.signal_open_pbar.connect(self._pbar_open)
        self.signal_close_pbar.connect(self._pbar_close)
        self.signal_increment_pbar.connect(self._pbar_increment)
        self.signal_set_pbar_value.connect(self._pbar_set_value)
        self.signal_error.connect(self._show_error)

        if show:
            self.show()

    def _install_type_changed(self, *args):
        self.python_version_select.setEnabled(
            self.installation_type_select.currentText() == "Standard"
        )

    def pbar_increment(self):
        """Increment the progress bar.

        Thread safe.
        """
        self.signal_increment_pbar.emit()

    def _pbar_increment(self):
        """Increment the progress bar.
        Not to be accessed outside of the main thread.
        """
        if self._pbar is not None:
            self._pbar.increment()

    def pbar_open(self, nticks=5, label=""):
        """Open the progress bar."""
        self.signal_open_pbar.emit(nticks, label)

    def _pbar_open(self, nticks, label):
        """Open the progress bar.

        Not to be accessed outside of the main thread.
        """
        if self._pbar is None:
            self._pbar = ProgressBar(self, nticks=nticks, label=label)

    def pbar_close(self):
        """Close the progress bar."""
        self.signal_close_pbar.emit()

    def _pbar_close(self):
        """Close the progress bar.

        Not to be accessed outside of the main thread.
        """
        if self._pbar is not None:
            self._pbar.close()
            self._pbar = None

    def pbar_set_value(self, value):
        """Set progress bar position.

        Thread safe.
        """
        self.signal_set_pbar_value.emit(value)

    def _pbar_set_value(self, value):
        """Set progress bar position.

        Not to be accessed outside of the main thread.
        """
        if self._pbar is not None:
            self._pbar.set_value(value)

    def error_dialog(self, txt, textinfo=None):
        """Create an error dialogue."""
        self._err_message_box = QtWidgets.QMessageBox(self)
        self._err_message_box.setIcon(QtWidgets.QMessageBox.Critical)
        self._err_message_box.setText(txt)

    def _show_error(self, text):
        """Display an error."""
        self._err_message_box = QtWidgets.QMessageBox(self)
        self._err_message_box.setIcon(QtWidgets.QMessageBox.Critical)
        self._err_message_box.setText(text)
        self._err_message_box.show()

    def show_error(self, text):
        """Thread safe show error."""
        LOG.error(text)
        self.signal_error.emit(text)

    def download_and_install(self):
        """Download and install."""
        self.setEnabled(False)
        QtWidgets.QApplication.processEvents()

        try:
            if self.installation_type_select.currentData() == "vanilla":
                selected_version = (
                    self.python_version_select.currentData()
                )  # should be major, minor, patch
                url = f"https://www.python.org/ftp/python/{selected_version}/python-{selected_version}-amd64.exe"
                filename = f"python-{selected_version}-amd64.exe"
                LOG.info("Installing vanilla Python %s", selected_version)
            else:
                url = "https://github.com/conda-forge/miniforge/releases/download/22.11.1-4/Miniforge3-22.11.1-4-Windows-x86_64.exe"
                filename = "Miniforge3-22.11.1-4-Windows-x86_64.exe"
                LOG.info("Installing miniconda from %s", url)

            self._download(url, filename, when_finished=self._run_exe)
        except Exception as e:
            self.show_error(str(e))
            self.setEnabled(True)

    @threaded
    def _download(self, url, filename, when_finished=None):
        """Download a file with a progress bar.

        Checks cache first. If cached file exists and is the same size
        as the file to be downloade, uses cached file.

        ``when_finished`` must accept one parameter, the path of the file downloaded.

        """
        from ansys.tools.installer import CACHE_DIR

        output_path = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(output_path):
            LOG.debug("%s exists at in %s", filename, CACHE_DIR)
            response = requests.head(url, allow_redirects=True)
            content_length = int(response.headers["Content-Length"])
            file_sz = os.path.getsize(output_path)
            if content_length == file_sz:
                LOG.debug("Sizes match. Using cached file from %s", output_path)
                if when_finished is not None:
                    when_finished(output_path)
                return

            LOG.debug("Sizes do not match. Ignoring cached file.")

        # size and current_bytes, current bar position
        total = [None, 0, 0]

        def update(b=1, bsize=1, tsize=None):
            """Update download progress."""
            if tsize:
                total[0] = tsize
            total[1] += bsize
            if total[0] is not None:
                val = floor(100 * total[1] / total[0])
                if total[2] != val:
                    self.pbar_set_value(val)

        def download():
            """Execute download."""
            self.pbar_open(100, f"Downloading {filename}")

            # first, query if the file exists
            response = requests.head(url, allow_redirects=True)

            if response.status_code != 200:
                self.show_error(
                    f"Unable to download {filename}.\n\nReceived {response.status_code} from {url}"
                )
                self.pbar_close()
                return ""

            total_size = None
            try:
                total[0] = int(response.headers["Content-Length"])
            except:
                total[0] = 50 * 2**20  # dummy 50 MB

            urllib.request.urlretrieve(url, filename=output_path, reporthook=update)
            self.pbar_close()

            if when_finished is not None:
                when_finished(output_path)

        Thread(target=download).start()

    def _run_exe(self, filename):
        """Execute a file."""
        LOG.debug("Executing run_exe")
        out, error = install_python(filename)

        LOG.debug("Triggering table widget update")
        self._table_tab.update_table()

        LOG.debug("Installing extra packages now...")
        self._extra_packages()

        self.setEnabled(True)

    def _extra_packages(self):
        """Install the requested extra packages."""
        python_path = None
        if self.installation_type_select.currentData() == "vanilla":
            minor_version = self.python_version_select.currentData().split(".")[1]
            python_path = find_installed_python(f"3.{minor_version}")
        else:
            conda_paths = find_miniforge()
            if len(conda_paths) != 1:
                LOG.warn(
                    "More than one conda install found... cannot resolve installation of extra packages."
                )
                return
            else:
                python_path = conda_paths.keys()[0]

        if not python_path:
            LOG.warn(
                "More than one conda install found... cannot resolve installation of extra packages."
            )
            return

        # WIP : We have access to the location of python.exe at this stage...
        pass


def open_gui():
    """Start the installer as a QT Application."""
    app = QtWidgets.QApplication(sys.argv)
    window = AnsysPythonInstaller()
    window.show()
    sys.exit(app.exec())

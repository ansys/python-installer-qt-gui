"""Main installer window."""


from math import floor
import os
import sys

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from packaging import version
import requests

from ansys.tools.installer import CACHE_DIR, __version__
from ansys.tools.installer.auto_updater import READ_ONLY_PAT, query_gh_latest_release
from ansys.tools.installer.common import protected, threaded
from ansys.tools.installer.constants import (
    ABOUT_TEXT,
    ASSETS_PATH,
    INSTALL_TEXT,
    LOG,
    PYTHON_VERSION_TEXT,
)
from ansys.tools.installer.create_virtual_environment import CreateVenvTab
from ansys.tools.installer.installed_table import InstalledTab
from ansys.tools.installer.installer import install_python, run_ps
from ansys.tools.installer.misc import ImageWidget, enable_logging
from ansys.tools.installer.progress_bar import ProgressBar


class AnsysPythonInstaller(QtWidgets.QMainWindow):
    """Main Ansys Python Manager class."""

    signal_error = QtCore.Signal(str)
    signal_open_pbar = QtCore.Signal(int, str)
    signal_increment_pbar = QtCore.Signal()
    signal_close_pbar = QtCore.Signal()
    signal_set_pbar_value = QtCore.Signal(int)
    signal_close = QtCore.Signal()

    def __init__(self, show=True):
        """Instantiate Ansys Python Manager main class."""
        super().__init__()
        self.setWindowTitle("Ansys Python Manager")
        self.setGeometry(50, 50, 500, 700)  # width should auto-update
        self._exceptions = []

        self._pbar = None
        self._err_message_box = None

        # Set the global font
        font = QtGui.QFont("Open Sans", -1, QtGui.QFont.Normal, False)
        QtWidgets.QApplication.setFont(font)

        # Create a QIcon object from an image file
        icon = QtGui.QIcon(os.path.join(ASSETS_PATH, "ansys-favicon.png"))
        # Set the application icon
        self.setWindowIcon(icon)

        # Create a menu bar
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        updates_action = QtGui.QAction("Check for Updates", self)
        updates_action.triggered.connect(self.check_for_updates)
        file_menu.addAction(updates_action)

        file_menu.addSeparator()  # -------------------------------------------

        # Create an "Exit" action
        exit_action = QtGui.QAction("&Exit", self)
        exit_action.setShortcut(QtGui.QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(QtWidgets.QApplication.quit)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("&Help")

        # Create a "Visit Website" action
        visit_action = QtGui.QAction("&Online Documentation", self)
        visit_action.triggered.connect(self.visit_website)
        help_menu.addAction(visit_action)

        # Create a "Report issue" action
        issue_action = QtGui.QAction("&Report issue", self)
        issue_action.triggered.connect(self.report_issue)
        help_menu.addAction(issue_action)

        help_menu.addSeparator()  # -------------------------------------------

        # Create an "About" action
        about_action = QtGui.QAction("&About", self)
        about_action.triggered.connect(self.show_about_dialog)

        # Add the "About" action to the "Help" menu
        help_menu.addAction(about_action)

        # Header
        header_layout = QtWidgets.QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_widget = QtWidgets.QWidget()
        header_widget.setLayout(header_layout)

        # Header icon
        self.menu_heading = ImageWidget()
        pixmap = QtGui.QPixmap(os.path.join(ASSETS_PATH, "pyansys-light-crop.png"))
        self.menu_heading.setPixmap(pixmap)
        header_layout.addWidget(self.menu_heading)

        # Main content
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_install_python = QtWidgets.QWidget()
        self.tab_widget.addTab(self.tab_install_python, "Install Python")

        # Add tabs to the tab widget
        self.installed_table_tab = InstalledTab(self)
        self.venv_table_tab = CreateVenvTab(self)
        self.tab_widget.addTab(self.venv_table_tab, "Create Virtual Environments")
        self.tab_widget.addTab(self.installed_table_tab, "Manage Python Environments")

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
        installation_type_text.setOpenExternalLinks(True)
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

        # ensure content does not get squished
        form_layout.addStretch()

        # Submit button
        self.submit_button = QtWidgets.QPushButton("Install")
        self.submit_button.setStyleSheet("background-color: #ffb71b")
        self.submit_button.clicked.connect(self.download_and_install)
        form_layout.addWidget(self.submit_button)

        container_layout.addWidget(form)

        # Add menu and tab widget to main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(header_widget)
        main_layout.addWidget(self.tab_widget)

        # create central widget
        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # connects
        self.signal_open_pbar.connect(self._pbar_open)
        self.signal_close_pbar.connect(self._pbar_close)
        self.signal_increment_pbar.connect(self._pbar_increment)
        self.signal_set_pbar_value.connect(self._pbar_set_value)
        self.signal_error.connect(self._show_error)
        self.signal_close.connect(self._close)

        if show:
            self.show()

    @protected
    def _exe_update(self, filename):
        """After downloading the update for this application, run the file and shutdown this application."""
        run_ps(f"(Start-Process {filename})")

        # exiting
        LOG.debug("Closing...")
        self.close_emit()

    def close_emit(self):
        """Trigger the exit signal."""
        self.signal_close.emit()

    def _close(self):
        self.close()

    @protected
    def check_for_updates(self):
        """Check for Ansys Python Manager application updates."""
        LOG.debug("Checking for updates")
        (
            ver,
            url,
        ) = query_gh_latest_release()
        cur_ver = version.parse(__version__)

        LOG.debug(f"Currently installed version: {cur_ver}")
        LOG.debug(f"Latest version: {ver}")

        if ver > cur_ver:
            LOG.debug("Update available.")
            pixmap = QPixmap("assets/ansys-favicon.png").scaledToHeight(
                32, Qt.SmoothTransformation
            )

            msgBox = QtWidgets.QMessageBox()
            msgBox.setWindowIcon(QtGui.QIcon("assets/ansys-favicon.png"))
            msgBox.setIconPixmap(pixmap)

            reply = msgBox.question(
                msgBox,
                "Update",
                f"The latest available version is {ver}. You are currently running version {cur_ver}. Do you want to update?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.Yes,
            )

            if reply == QtWidgets.QMessageBox.Yes:
                self._download(
                    url,
                    f"Ansys-Python-Manager-Setup-v{ver}.exe",
                    when_finished=self._exe_update,
                    auth=READ_ONLY_PAT,
                )
        else:
            LOG.debug("Up to date.")
            msgBox = QtWidgets.QMessageBox(
                QtWidgets.QMessageBox.Information,
                "Information",
                f"Ansys Python Installer is up-to-date.\n\nVersion is {__version__}",
                QtWidgets.QMessageBox.Ok,
            )
            msgBox.setWindowIcon(QtGui.QIcon("assets/ansys-favicon.png"))
            pixmap = QPixmap("assets/ansys-favicon.png").scaledToHeight(
                32, Qt.SmoothTransformation
            )
            msgBox.setIconPixmap(pixmap)
            msgBox.exec_()

    def visit_website(self):
        """Access the Ansys Python Manager documentation."""
        url = QtCore.QUrl(
            "https://installer.docs.pyansys.com/version/dev/installer.html"
        )
        QtGui.QDesktopServices.openUrl(url)

    def report_issue(self):
        """Access the Ansys Python Manager issues tracker."""
        url = QtCore.QUrl("https://github.com/pyansys/python-installer-qt-gui/issues")
        QtGui.QDesktopServices.openUrl(url)

    def show_about_dialog(self):
        """Display the Ansys Python Manager 'About' information."""
        mbox = QtWidgets.QMessageBox.about(self, "About", ABOUT_TEXT)

    def _install_type_changed(self, *args):
        if self.installation_type_select.currentText() == "Standard":
            self.python_version_select.setEnabled(True)
        elif self.installation_type_select.currentText() == "Conda (miniforge)":
            default_index = self.python_version_select.findText("Python 3.10")
            self.python_version_select.setCurrentIndex(default_index)
            self.python_version_select.setEnabled(False)

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
        """Open the progress bar.

        Parameters
        ----------
        nticks : int, default: 5
            Number of "ticks" to set the progress bar to.

        label : str, default: ""
            Label of the progress bar.

        """
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

        Parameters
        ----------
        value : int
            Value to set active progress bar to.

        """
        self.signal_set_pbar_value.emit(value)

    def _pbar_set_value(self, value):
        """Set progress bar position.

        Not to be accessed outside of the main thread.

        Parameters
        ----------
        value : int
            Value to set active progress bar to.

        """
        if self._pbar is not None:
            self._pbar.set_value(value)

    def _show_error(self, text):
        """Display an error.

        Not thread safe. Call ``show_error`` instead for thread safety.

        Parameters
        ----------
        text : str
            Message to display as an error.

        """
        if not isinstance(text, str):
            text = str(text)
        self._err_message_box = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Critical,
            "Error",
            text,
            QtWidgets.QMessageBox.Ok,
        )
        self._err_message_box.show()

    def show_error(self, text):
        """Thread safe show error.

        This can be called from any thread.

        Parameters
        ----------
        text : str
            Message to display as an error.

        """
        LOG.error(text)
        self.signal_error.emit(text)

    def download_and_install(self):
        """Download and install.

        Called when ``self.submit_button.clicked`` is emitted.

        """
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
    def _download(self, url, filename, when_finished=None, auth=None):
        """Download a file with a progress bar.

        Checks cache first. If cached file exists and is the same size
        as the file to be downloade, uses cached file.

        ``when_finished`` must accept one parameter, the path of the file downloaded.

        Parameters
        ----------
        url : str
            File to download.

        filename : str
            The basename of the file to download.

        when_finished : callable, optional
            Function to call when complete. Function should accept one
            parameter: the full path of the file downloaded.

        auth : str, optional
            Authorization token for GitHub. This is used when
            downloading release artifacts from private/internal
            repositories.

        """
        request_headers = {}
        if auth:
            request_headers = {
                "Authorization": f"token {READ_ONLY_PAT}",
                "Accept": "application/octet-stream",
            }

        # initiate the download
        session = requests.Session()
        response = session.get(
            url, allow_redirects=True, stream=True, headers=request_headers
        )
        tsize = int(response.headers.get("Content-Length", 0))

        if response.status_code != 200:
            self.show_error(
                f"Unable to download {filename}.\n\nReceived {response.status_code} from {url}"
            )
            self.pbar_close()
            return

        output_path = os.path.join(CACHE_DIR, filename)
        if os.path.isfile(output_path) and tsize:
            LOG.debug("%s exists at in %s", filename, CACHE_DIR)
            file_sz = os.path.getsize(output_path)
            if tsize == file_sz:
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

        self.pbar_open(100, f"Downloading {filename}")

        chunk_size = 200 * 1024  # 200kb
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size):
                f.write(chunk)
                update(0, chunk_size, tsize)
                tsize = None

        self.pbar_close()

        if when_finished is not None:
            when_finished(output_path)

    def _run_exe(self, filename):
        """Execute a file."""
        LOG.debug("Executing run_exe")
        out, error = install_python(filename)

        LOG.debug("Triggering table widget update")
        self.installed_table_tab.update_table()
        self.venv_table_tab.update_table()

        self.setEnabled(True)


def open_gui():
    """Start the installer as a QT Application."""
    import argparse
    import ctypes
    import msvcrt

    kernel32 = ctypes.windll.kernel32

    # Parse command-line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--console", action="store_true", help="Open console window")
    try:
        args = parser.parse_args()
    except AttributeError:
        kernel32.AllocConsole()

        # Redirect stdout and stderr to the console
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")

        try:
            args = parser.parse_args()
        except SystemExit:
            print("\nPress any key to continue...")
            msvcrt.getch()
            return

    # Allocate console if --console option is specified
    if args.console:
        kernel32.AllocConsole()

        # Redirect stdout and stderr to the console
        sys.stdout = open("CONOUT$", "w")
        sys.stderr = open("CONOUT$", "w")

    enable_logging()

    app = QtWidgets.QApplication(sys.argv)
    window = AnsysPythonInstaller()
    window.show()
    sys.exit(app.exec())

import os
from PySide6 import QtWidgets, QtGui, QtCore
import sys

INSTALL_TEXT = """Choose to use either the standard Python install from <a href='https://www.python.org/'>python.org</a> or <a href='https://github.com/conda-forge/miniforge'>miniforge</a>."""

PYTHON_VERSION_TEXT = """Choose the version of Python to install.

While choosing the latest version of Python is generally recommended, some third-party libraries and applications may not yet be fully compatible with the newest release. Therefore, it is recommended to try the second newest version, as it will still have most of the latest features and improvements while also having broader support among third-party packages."""

PACKAGES_INFO_TEXT = """Select the packages to install globally in the Python enviornment. By default, the "Default" and "PyAnsys" packages are selected, but the user can also choose to install "Jupyterlab" or "Spyder (IDE)" by selecting the corresponding check boxes. This allows the user to customize their Python installation to suit their specific needs."""

THIS_PATH = os.path.dirname(os.path.abspath(__file__))
ASSETS_PATH = os.path.join(THIS_PATH, 'assets')

class AnsysPythonInstaller(QtWidgets.QWidget):
    def __init__(self, show=True):
        super().__init__()
        self.setWindowTitle("Ansys Python Installer")

        # Set the global font
        font = QtGui.QFont('Open Sans', -1, QtGui.QFont.Normal, False)
        QtWidgets.QApplication.setFont(font)

        # Create a QIcon object from an image file
        icon = QtGui.QIcon(os.path.join(ASSETS_PATH, "ansys-favicon.png"))
        # Set the application icon
        self.setWindowIcon(icon)

        # Menu
        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.setContentsMargins(0,0,0,0)
        menu_widget = QtWidgets.QWidget()
        menu_widget.setObjectName("menu")
        menu_widget.setLayout(menu_layout)

        self.menu_heading = QtWidgets.QLabel()
        pixmap = QtGui.QPixmap(os.path.join(ASSETS_PATH, "pyansys-light-crop.png"))
        self.menu_heading.setPixmap(pixmap)
        menu_layout.addWidget(self.menu_heading)

        # Main content
        self.tab_widget = QtWidgets.QTabWidget()
        self.tab_widget.setObjectName("tab_widget")
        self.container = QtWidgets.QWidget()
        self.container.setObjectName("container")
        self.tab_widget.addTab(self.container, "Install Python")

        # Add tabs to the tab widget
        self.tab_widget.addTab(QtWidgets.QWidget(), "Tab 2")
        self.tab_widget.addTab(QtWidgets.QWidget(), "Tab 3")
        self.tab_widget.addTab(QtWidgets.QWidget(), "Tab 4")

        # Create the layout for the container
        container_layout = QtWidgets.QVBoxLayout()
        # container_layout.setAlignment(QtCore.Qt.AlignCenter)
        self.container.setLayout(container_layout)

        # Form
        form = QtWidgets.QWidget()
        form.setObjectName("form")
        form_layout = QtWidgets.QVBoxLayout()
        form_layout.setContentsMargins(0,0,0,0)
        form.setLayout(form_layout)

        # Installation type
        installation_type_box = QtWidgets.QGroupBox("Installation Type")
        installation_type_box_layout = QtWidgets.QVBoxLayout()
        installation_type_box_layout.setContentsMargins(10, 20, 10, 20)
        installation_type_box.setLayout(installation_type_box_layout)

        # Group 1: Installation type
        installation_type = QtWidgets.QWidget()
        installation_type.setObjectName("installation-type")
        installation_type_layout = QtWidgets.QVBoxLayout()
        installation_type_layout.setContentsMargins(0,0,0,0)
        installation_type.setLayout(installation_type_layout)

        installation_type_text = QtWidgets.QLabel(INSTALL_TEXT)
        installation_type_text.setObjectName("card-text")
        installation_type_layout.addWidget(installation_type_text)

        installation_type_select = QtWidgets.QComboBox()
        installation_type_select.setObjectName("python-type")
        installation_type_select.addItem("Standard", "vanilla")
        installation_type_select.addItem("Conda (miniforge)", "miniconda")
        installation_type_layout.addWidget(installation_type_select)

        installation_type_box_layout.addWidget(installation_type)
        form_layout.addWidget(installation_type_box)

        # Group 2: Python version
        python_version_box = QtWidgets.QGroupBox("Python Version")
        python_version_box_layout = QtWidgets.QVBoxLayout()
        python_version_box_layout.setContentsMargins(10, 20, 10, 20)
        python_version_box.setLayout(python_version_box_layout)

        python_version_text = QtWidgets.QLabel(PYTHON_VERSION_TEXT)
        python_version_text.setObjectName("card-text")
        python_version_text.setWordWrap(True)
        python_version_box_layout.addWidget(python_version_text)

        # Python version
        python_version = QtWidgets.QWidget()
        python_version.setObjectName("python-version")
        python_version_layout = QtWidgets.QVBoxLayout()
        python_version_layout.setContentsMargins(0,0,0,0)
        python_version.setLayout(python_version_layout)

        # python_version_title = QtWidgets.QLabel("Python Version")
        # python_version_title.setObjectName("card-title")
        # python_version_layout.addWidget(python_version_title)

        # python_version_text = QtWidgets.QLabel("Select one")

        python_version_select = QtWidgets.QComboBox()
        python_version_select.setObjectName("python-version")
        python_version_select.addItem("Python 3.7", "3.7.9")
        python_version_select.addItem("Python 3.8", "3.8.10")
        python_version_select.addItem("Python 3.9", "3.9.13")
        python_version_select.addItem("Python 3.10", "3.10.10")
        python_version_select.addItem("Python 3.11", "3.11.2")

        # Set the default selection to "Python 3.10"
        default_index = python_version_select.findText("Python 3.10")
        python_version_select.setCurrentIndex(default_index)
        python_version_layout.addWidget(python_version_select)

        python_version_box_layout.addWidget(python_version)
        form_layout.addWidget(python_version_box)

        # Group 3: Packages
        packages_box = QtWidgets.QGroupBox("Packages")
        packages_box_layout = QtWidgets.QVBoxLayout()
        packages_box_layout.setContentsMargins(10, 20, 10, 20)
        packages_box.setLayout(packages_box_layout)

        # Packages
        packages = QtWidgets.QWidget()
        packages.setObjectName("packages")
        packages_layout = QtWidgets.QVBoxLayout()
        # packages_layout.setContentsMargins(0,0,0,0)
        packages.setLayout(packages_layout)

        packages_info_text = QtWidgets.QLabel(PACKAGES_INFO_TEXT)
        packages_info_text.setObjectName("card-text")
        packages_info_text.setWordWrap(True)
        packages_layout.addWidget(packages_info_text)

        packages_default = QtWidgets.QCheckBox("Default")
        packages_default.setObjectName("packages-default")
        packages_default.setChecked(True)
        packages_layout.addWidget(packages_default)

        packages_pyansys = QtWidgets.QCheckBox("PyAnsys")
        packages_pyansys.setObjectName("packages-pyansys")
        packages_pyansys.setChecked(True)
        packages_layout.addWidget(packages_pyansys)

        packages_jupyterlab = QtWidgets.QCheckBox("Jupyterlab")
        packages_jupyterlab.setObjectName("packages-jupyterlab")
        packages_layout.addWidget(packages_jupyterlab)

        packages_spyder = QtWidgets.QCheckBox("Spyder (IDE)")
        packages_spyder.setObjectName("packages-spyder")
        packages_layout.addWidget(packages_spyder)

        packages_box_layout.addWidget(packages)
        form_layout.addWidget(packages_box)

        # ensure content does not get squished
        form_layout.addStretch()

        # Submit button
        submit_button = QtWidgets.QPushButton("Install")
        submit_button.setObjectName("install-btn")
        submit_button.setProperty("class", "btn-large waves-effect waves-light button-ansys")
        form_layout.addWidget(submit_button)

        container_layout.addWidget(form)

        # Add menu and tab widget to main layout
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.setContentsMargins(0,0,0,0)
        main_layout.addWidget(menu_widget)
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)

        if show:
            self.show()


def open_gui():
    """Start the installer as a QT Application."""
    app = QtWidgets.QApplication(sys.argv)
    window = AnsysPythonInstaller()
    window.show()
    sys.exit(app.exec())

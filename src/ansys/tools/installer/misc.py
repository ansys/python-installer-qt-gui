"""Contains miscellaneous functionalities this library."""

import logging
import sys

from PySide6 import QtCore, QtGui, QtWidgets

from ansys.tools.installer.constants import (
    ANSYS_FAVICON,
    PYANSYS_DOCS_SITES,
    PYANSYS_DOCS_TEXT,
)


def enable_logging():
    """Log to stdout."""

    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                if not self.stream.closed:
                    super().emit(record)
            except (ValueError, AttributeError):
                pass

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a console handler that writes to stdout
    console_handler = SafeStreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)


class ImageWidget(QtWidgets.QLabel):
    """Automatic scaled image widget."""

    def __init__(self, parent=None):
        """Instantiate an ImageWidget."""
        super().__init__(parent)
        self.setScaledContents(True)

    def hasHeightForWidth(self):
        """Override height for width for autoscaling (when pixmap)."""
        return self.pixmap() is not None

    def heightForWidth(self, w):
        """Override height for width for autoscaling."""
        if self.pixmap():
            return int(w * (self.pixmap().height() / self.pixmap().width()))


class PyAnsysDocsBox(QtWidgets.QMessageBox):
    """PyAnsys documentation message box."""

    def __init__(self, parent=None):
        """Instantiate a PyAnsysDocsBox."""
        super().__init__(parent)
        self.setWindowTitle("PyAnsys Documentation")
        pixmap = QtGui.QPixmap(ANSYS_FAVICON).scaledToHeight(
            32, QtCore.Qt.SmoothTransformation
        )
        self.setWindowIcon(QtGui.QIcon(ANSYS_FAVICON))
        self.setIconPixmap(pixmap)
        self.setText(PYANSYS_DOCS_TEXT)

        # create a combo box and add items
        self.comboBox = QtWidgets.QComboBox(self)
        for key, value in PYANSYS_DOCS_SITES.items():
            self.comboBox.addItem(key, value)
        sizePolicy = QtWidgets.QSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.comboBox.setSizePolicy(sizePolicy)

        # create a button
        self.pushButton = QtWidgets.QPushButton("Open Website", self)
        self.pushButton.setSizePolicy(sizePolicy)

        # add the combo box and button to the message box
        layout = self.layout()
        layout.addWidget(self.comboBox, layout.rowCount(), 0, 1, layout.columnCount())
        layout.addWidget(self.pushButton, layout.rowCount(), 0, 1, layout.columnCount())

        # connect the button to a slot that opens the selected website
        self.pushButton.clicked.connect(self.open_website)

    def open_website(self):
        """Open the URL to the docs site chosen."""
        # get the selected index
        index = self.comboBox.currentIndex()

        # get the URL for the selected index
        url = self.comboBox.itemData(index)

        # open the corresponding website
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

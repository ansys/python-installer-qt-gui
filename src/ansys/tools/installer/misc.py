"""Contains miscellaneous functionalities this library."""

import logging
import sys

from PySide6 import QtWidgets


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

"""Progress bar module for Ansys Python Manager."""
from PySide6 import QtCore, QtWidgets


class ProgressBar(QtWidgets.QDialog):
    """ProgressBar class."""

    def __init__(self, parent, nticks, title="Progress Bar", label=None, show=True):
        """Instantiate a ProgressBar object."""
        super().__init__(parent)
        self._pbar = QtWidgets.QProgressBar(self)
        self._pbar.setValue(0)
        # self._pbar.setGeometry(30, 40, 500, 75)
        self.layout = QtWidgets.QVBoxLayout()
        if label:
            label_widget = QtWidgets.QLabel()
            label_widget.setText(label)
            label_widget.setSizePolicy(
                QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
            )
            label_widget.setAlignment(QtCore.Qt.AlignCenter)
            self.layout.addWidget(label_widget)
        self.layout.addWidget(self._pbar)
        self.setLayout(self.layout)
        self.setGeometry(300, 300, 550, 100)
        self.setWindowTitle(title)
        if show:
            self.show()

        # total number of values for QProgressBar is 100
        self._increment_value = 100 // nticks

    def increment(self):
        """Increments bar."""
        self._pbar.setValue(self._pbar.value() + self._increment_value)

    def set_value(self, value):
        """Set the value of the progress bar."""
        self._pbar.setValue(value)

    @property
    def value(self):
        """Return the value of the progress bar."""
        return self._pbar.value()

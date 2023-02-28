import sys

from PySide6.QtWidgets import QApplication
import pytest

from ansys.tools.installer import AnsysPythonInstaller


@pytest.fixture()
def gui():
    # ["--platform", "offscreen"]
    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    return AnsysPythonInstaller(show=False)

import os
import sys

from PySide6.QtWidgets import QApplication
import pytest

from ansys.tools.installer import AnsysPythonInstaller

@pytest.fixture(scope="session")
def gui():
    app = QApplication(["-platform", "offscreen"])
    return AnsysPythonInstaller(show=False)

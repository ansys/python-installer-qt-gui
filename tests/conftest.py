import pytest

from ansys.tools.installer.main import AnsysPythonInstaller


@pytest.fixture()
def gui(qtbot):
    return AnsysPythonInstaller(show=False)

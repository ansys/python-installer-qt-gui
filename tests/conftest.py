import pytest

from ansys.tools.installer import AnsysPythonInstaller


@pytest.fixture()
def gui(qtbot):
    return AnsysPythonInstaller(show=False)

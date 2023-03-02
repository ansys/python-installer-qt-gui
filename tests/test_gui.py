from PySide6 import QtWidgets
import pytest
from pytestqt.qtbot import QtBot

from ansys.tools.installer.main import AnsysPythonInstaller


@pytest.fixture(scope="session")
def qtbot_session(qapp, request):
    result = QtBot(qapp)
    yield result


@pytest.fixture(scope="session")
def gui(qtbot_session):
    installer = AnsysPythonInstaller(show=False)
    yield installer
    # qtbot_session.wait(1000)
    installer.close()


def test_main_window_header(gui):
    assert isinstance(gui.menu_heading, QtWidgets.QLabel)

    # verify image loaded
    pixmap = gui.menu_heading.pixmap()
    assert pixmap is not None
    assert not pixmap.isNull()


def test_downloader(gui):
    # this URL is subject to change
    url = "https://cdn.jsdelivr.net/gh/belaviyo/download-with/samples/sample.png"

    files = []

    def when_finished(out_path):
        files.append(out_path)

    thread = gui._download(url, "sample.png", when_finished=when_finished)
    thread.join()
    assert len(files) == 1
    assert files[0].endswith("sample.png")

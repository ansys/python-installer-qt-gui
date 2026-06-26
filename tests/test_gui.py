# Copyright (C) 2023 - 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from PySide6 import QtWidgets
import pytest

from ansys.tools.installer.main import AnsysPythonInstaller


@pytest.fixture
def gui(qtbot):
    installer = AnsysPythonInstaller(show=False)
    qtbot.addWidget(installer)
    yield installer
    installer.close()
    installer.deleteLater()
    qtbot.wait(1)


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

    gui._download(url, "sample.png", when_finished=when_finished)
    assert len(files) == 1
    assert files[0].endswith("sample.png")

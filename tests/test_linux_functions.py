# Copyright (C) 2023 - 2026 ANSYS, Inc. and/or its affiliates.
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

import os

import ansys.tools.installer.linux_functions as linux_functions
from ansys.tools.installer.linux_functions import (
    execute_linux_command,
    get_conda_url_and_filename,
    get_vanilla_url_and_filename,
)


def test_get_vanilla_url_and_filename():
    url, filename = get_vanilla_url_and_filename("3.12.0")
    assert url == "https://www.python.org/ftp/python/3.12.0/Python-3.12.0.tar.xz"
    assert filename == "Python-3.12.0.tar.xz"


def test_get_conda_url_and_filename():
    url, filename = get_conda_url_and_filename("23.1.0-4")
    assert (
        url
        == "https://github.com/conda-forge/miniforge/releases/download/23.1.0-4/Miniforge3-23.1.0-4-Linux-x86_64.sh"
    )
    assert filename == "Miniforge3-23.1.0-4-Linux-x86_64.sh"


def test_execute_linux_command_falls_back_to_sh_on_wsl(monkeypatch):
    calls = []

    class DummyProc:
        def wait(self):
            return None

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return DummyProc()

    monkeypatch.setattr(linux_functions.shutil, "which", lambda *_: "/usr/bin/gnome-terminal")
    monkeypatch.setattr(linux_functions.subprocess, "Popen", fake_popen)
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-24.04")
    monkeypatch.setenv("HOME", os.environ.get("HOME", "/home/test"))
    monkeypatch.setenv("USER", os.environ.get("USER", "test"))

    execute_linux_command("echo ok")

    assert calls
    args, kwargs = calls[0]
    assert args[0] == ["sh", "-c", "echo ok"]
    assert kwargs["env"]["PATH"] == "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"


def test_execute_linux_command_uses_gnome_terminal_when_available(monkeypatch):
    calls = []

    class DummyProc:
        def wait(self):
            return None

    def fake_popen(*args, **kwargs):
        calls.append((args, kwargs))
        return DummyProc()

    monkeypatch.setattr(linux_functions.shutil, "which", lambda *_: "/usr/bin/gnome-terminal")
    monkeypatch.setattr(linux_functions.subprocess, "Popen", fake_popen)
    monkeypatch.delenv("WSL_DISTRO_NAME", raising=False)
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("HOME", os.environ.get("HOME", "/home/test"))
    monkeypatch.setenv("USER", os.environ.get("USER", "test"))

    execute_linux_command("echo ok")

    assert calls
    args, kwargs = calls[0]
    assert isinstance(args[0], str)
    assert "gnome-terminal --wait -- sh -c 'echo ok'" in args[0]
    assert kwargs["shell"] is True

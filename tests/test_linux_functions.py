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

import pytest

from ansys.tools.installer.linux_functions import (
    NoLinuxTerminalError,
    execute_linux_command,
    find_linux_terminal,
    get_conda_url_and_filename,
    get_vanilla_url_and_filename,
    run_linux_command,
    run_linux_command_conda,
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


def test_run_linux_command_accepts_working_dir():
    """Verify run_linux_command and run_linux_command_conda accept working_dir kwarg."""
    import inspect

    sig = inspect.signature(run_linux_command)
    assert "working_dir" in sig.parameters

    sig_conda = inspect.signature(run_linux_command_conda)
    assert "working_dir" in sig_conda.parameters


def test_find_linux_terminal_returns_none_when_no_terminal_available(monkeypatch):
    """No terminal emulator should be found when none are on the PATH."""
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which", lambda _name: None
    )
    assert find_linux_terminal() is None


def test_find_linux_terminal_finds_non_gnome_terminal(monkeypatch):
    """A non gnome-terminal emulator (e.g. xterm) should still be detected."""
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which",
        lambda name: "/usr/bin/xterm" if name == "xterm" else None,
    )
    assert find_linux_terminal() == "xterm"


def test_execute_linux_command_raises_clear_error_without_terminal(monkeypatch):
    """execute_linux_command should raise a clear, actionable error (e.g. on WSL)."""
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which", lambda _name: None
    )
    with pytest.raises(NoLinuxTerminalError):
        execute_linux_command("echo hello")


def test_execute_linux_command_uses_available_terminal(monkeypatch):
    """execute_linux_command should use whichever supported terminal is found."""
    calls = []
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which",
        lambda name: "/usr/bin/xterm" if name == "xterm" else None,
    )
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.subprocess.run",
        lambda argv: calls.append(argv),
    )
    execute_linux_command("echo hello", wait=True)
    assert len(calls) == 1
    assert calls[0][0] == "xterm"
    assert "echo hello" in calls[0]

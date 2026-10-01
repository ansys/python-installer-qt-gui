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
    create_venv_linux,
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


@pytest.mark.parametrize(
    "available, expected",
    [({"apt-get"}, "sudo apt-get install xterm"), ({"dnf"}, "sudo dnf install xterm")],
)
def test_no_terminal_error_suggests_distro_package_manager(
    monkeypatch, available, expected
):
    """The install hint must match the distro's package manager (apt vs dnf)."""
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in available else None,
    )
    with pytest.raises(NoLinuxTerminalError, match=expected):
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
        lambda argv, **_kwargs: calls.append(argv),
    )
    execute_linux_command("echo hello", wait=True)
    assert len(calls) == 1
    assert calls[0][0] == "xterm"
    assert "echo hello" in calls[0]


@pytest.mark.parametrize(
    "frozen, env_in, expected",
    [
        # PyInstaller saved the user's original value: restore it.
        (
            True,
            {"LD_LIBRARY_PATH": "/app/_internal", "LD_LIBRARY_PATH_ORIG": "/u"},
            "/u",
        ),
        # User had none: the bundle path must not leak into the terminal.
        (True, {"LD_LIBRARY_PATH": "/app/_internal"}, None),
        # Not frozen: leave the user's environment untouched.
        (False, {"LD_LIBRARY_PATH": "/u"}, "/u"),
    ],
)
@pytest.mark.parametrize("wait", [True, False])
def test_execute_linux_command_does_not_leak_bundle_libraries(
    monkeypatch, frozen, env_in, expected, wait
):
    """Terminals must not inherit the frozen app's bundled library path."""
    envs = []
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.shutil.which",
        lambda name: "/usr/bin/xterm" if name == "xterm" else None,
    )
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.subprocess.run",
        lambda argv, env=None, **_kwargs: envs.append(env),
    )
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.subprocess.Popen",
        lambda argv, env=None, **_kwargs: envs.append(env),
    )
    monkeypatch.delenv("LD_LIBRARY_PATH", raising=False)
    monkeypatch.delenv("LD_LIBRARY_PATH_ORIG", raising=False)
    for key, value in env_in.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("sys.frozen", frozen, raising=False)

    execute_linux_command("echo hello", wait=wait)

    assert len(envs) == 1
    assert envs[0].get("LD_LIBRARY_PATH") == expected
    assert "LD_LIBRARY_PATH_ORIG" not in envs[0]


@pytest.fixture
def linux_commands(monkeypatch):
    """Record the commands sent to the terminal instead of running them."""
    commands = []
    monkeypatch.setattr(
        "ansys.tools.installer.linux_functions.execute_linux_command",
        lambda command, wait=True: commands.append(command),
    )
    return commands


def test_create_venv_linux_seeds_pip_and_uv(linux_commands):
    """Venvs must contain pip and uv, which package management relies on."""
    create_venv_linux("/home/u/venvs/my env", "/home/u/python-3.11/bin/python3")
    assert linux_commands == [
        "/home/u/python-3.11/bin/python3 -m pip install -U pip uv",
        "/home/u/python-3.11/bin/python3 -m uv venv --seed '/home/u/venvs/my env'",
        "'/home/u/venvs/my env/bin/python' -m pip install -U pip uv",
    ]


def test_run_linux_command_venv_uses_venv_python(linux_commands):
    """Updates must run with the venv's interpreter, not the venv folder."""
    run_linux_command("/home/u/venvs/env1", "uv pip list", venv=True)
    update, command = linux_commands
    python = "/home/u/venvs/env1/bin/python"
    assert update == (
        f"{python} -m pip --version >/dev/null 2>&1 || "
        f"{python} -m ensurepip --upgrade; {python} -m pip install -U pip uv"
    )
    assert ". /home/u/venvs/env1/bin/activate; uv pip list" in command


def test_run_linux_command_base_python_targets_selected_interpreter(linux_commands):
    """``uv --system`` and ``python`` must resolve to the selected interpreter."""
    python = "/home/u/python-3.11/bin/python3"
    run_linux_command(
        python,
        "uv pip install --system numpy && python -m jupyter lab && timeout 3",
    )
    update, command = linux_commands
    assert update == f"{python} -m pip install -U pip uv"
    assert 'PATH=/home/u/python-3.11/bin:"$PATH"; export PATH; ' in command
    assert f"uv pip install --python {python} numpy" in command
    assert f"{python} -m jupyter lab" in command
    assert "--system" not in command
    assert "sleep 3" in command


def test_run_linux_command_base_python_console(linux_commands):
    """The console must start a regular shell with the interpreter on the PATH."""
    run_linux_command("/home/u/python-3.11/bin/python3", "")
    assert linux_commands[1] == (
        'cd ~ ; PATH=/home/u/python-3.11/bin:"$PATH"; export PATH; bash'
    )

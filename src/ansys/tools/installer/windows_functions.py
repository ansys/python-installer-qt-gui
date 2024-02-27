# Copyright (C) 2023 - 2024 ANSYS, Inc. and/or its affiliates.
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

"""Windows functions."""

import os
import subprocess


def create_venv_windows(venv_dir: str, py_path: str):
    r"""
    Create a virtual environment on Windows.

    Parameters
    ----------
    venv_dir : str
        Name of the virtual environment.
    py_path : str
        Path to the Python executable.

    Examples
    --------
    >>> create_venv_windows("my_venv", "C:\\Python39\\python.exe")

    """
    user_profile = os.path.expanduser("~")
    scripts_path = os.path.join(py_path, "Scripts")
    new_path = f"{py_path};{scripts_path};%PATH%"
    subprocess.call(
        f'start /w /min cmd /K "set PATH={new_path} && python -m venv {venv_dir} && exit"',
        shell=True,
        cwd=user_profile,
    )


def create_venv_windows_conda(venv_dir: str, py_path: str):
    r"""
    Create a virtual environment on Windows using conda.

    Parameters
    ----------
    venv_dir : str
        Name of the virtual environment.
    py_path : str
        Path to the Python executable.

    Examples
    --------
    >>> create_venv_windows_conda("my_venv", "C:\\Python39\\python.exe")

    """
    user_profile = os.path.expanduser("~")
    subprocess.call(
        f'start /w /min cmd /K "{py_path}\\Scripts\\activate.bat && conda create --prefix {venv_dir} python -y && exit"',
        shell=True,
        cwd=user_profile,
    )

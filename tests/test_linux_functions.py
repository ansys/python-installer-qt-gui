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

from ansys.tools.installer.linux_functions import (
    get_conda_url_and_filename,
    get_vanilla_url_and_filename,
)


def test_get_vanilla_url_and_filename():
    url, filename = get_vanilla_url_and_filename("3.8.11")
    assert url == "https://www.python.org/ftp/python/3.8.11/Python-3.8.11.tar.xz"
    assert filename == "Python-3.8.11.tar.xz"


def test_get_conda_url_and_filename():
    url, filename = get_conda_url_and_filename("23.1.0-4")
    assert (
        url
        == "https://github.com/conda-forge/miniforge/releases/download/23.1.0-4/Miniforge3-23.1.0-4-Linux-x86_64.sh"
    )
    assert filename == "Miniforge3-23.1.0-4-Linux-x86_64.sh"

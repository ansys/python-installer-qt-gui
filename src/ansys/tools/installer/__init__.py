# Copyright (C) 2023 - 2025 ANSYS, Inc. and/or its affiliates.
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

"""Ansys Python Manager."""

import os
import sys
import warnings

from appdirs import user_cache_dir

if getattr(sys, "frozen", False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    try:
        _THIS_PATH = sys._MEIPASS
    except:
        # this might occur on a single file install
        os.path.dirname(sys.executable)
else:
    _THIS_PATH = os.path.dirname(os.path.abspath(__file__))

# Read in version programmatically from plain text
# this is done so NSIS can also link to the same version
with open(os.path.join(_THIS_PATH, "VERSION")) as fid:
    __version__ = fid.read()

CACHE_DIR = user_cache_dir("ansys_python_installer")

if not os.path.isdir(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except:
        import tempdir

        warnings.warn(f"Unable create cache at {CACHE_DIR}. Using temporary directory")
        CACHE_DIR = tempdir.gettempdir()


try:
    from ansys.tools.installer.main import open_gui  # place this at end to allow import
except ModuleNotFoundError:  # encountered during install
    pass

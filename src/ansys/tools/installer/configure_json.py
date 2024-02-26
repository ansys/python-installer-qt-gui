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

"""Configure json file."""

import json
import os

from ansys.tools.installer.constants import (
    ADDITIONAL_VENV_PATH,
    ANSYS_VENVS,
    VENV_CREATE_PATH,
    VENV_SEARCH_PATH,
)
from ansys.tools.installer.linux_functions import ansys_linux_path, is_linux_os


class ConfigureJson:
    """Configuration json class."""

    def __init__(self):
        """Instantiate Configuration class."""
        self.config_file_path = os.path.join(
            os.path.expanduser("~"), ".ansys", "ansys_python_manager", "config.json"
        )
        self.default_path = os.path.join(
            ansys_linux_path if is_linux_os() else os.path.expanduser("~"), ANSYS_VENVS
        )
        self.venv_search_path = [self.default_path]
        self.additional_venv_path = []
        self._create_config_file_if_not_exist()
        self._read_config_file()

    def _create_config_file_if_not_exist(self):
        """Create Configuration file if not exist."""
        if not os.path.exists(self.config_file_path) or (
            not os.path.getsize(self.config_file_path)
        ):
            os.makedirs(os.path.dirname(self.config_file_path), exist_ok=True)
            self.configs = {
                "path": {
                    VENV_CREATE_PATH: self.default_path,
                    VENV_SEARCH_PATH: [self.default_path],
                }
            }
            self._write_config_file()

    def _read_config_file(self):
        """Read Configuration file."""
        with open(self.config_file_path) as f:
            paths = json.load(f)
            self.default_path = paths["path"][VENV_CREATE_PATH]
            self.venv_search_path = paths["path"][VENV_SEARCH_PATH]
            self.configs = paths

    def rewrite_config_file(self, key, value):
        """Rewrite Configuration file.

        Parameters
        ----------
        key : str
            key to save the configuration

        value : str
            value to save the configuration

        """
        self.configs["path"][key] = value

    def _write_config_file(self):
        with open(self.config_file_path, "w+") as f:
            f.write(json.dumps(self.configs))
        self._read_config_file()

    def delete_venv_path(self, path):
        """Delete venv from Configuration file.

        Parameters
        ----------
        path : str
            Path of the venv

        """
        if path in self.configs["path"][ADDITIONAL_VENV_PATH]:
            self.configs["path"][ADDITIONAL_VENV_PATH].remove(path)
        self._write_config_file()

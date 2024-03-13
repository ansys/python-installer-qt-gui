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
    ANSYS_VENVS,
    VENV_DEFAULT_PATH,
    VENV_SEARCH_PATH,
)
from ansys.tools.installer.linux_functions import ansys_linux_path, is_linux_os


class ConfigureJson:
    """Configuration json class."""

    def __init__(self):
        """Instantiate Configuration class."""
        self.config_dir = os.path.join(
            os.path.expanduser("~"), ".ansys", "ansys_python_manager"
        )
        self.config_file_path = os.path.join(self.config_dir, "config.json")

        self.history_file_path = os.path.join(self.config_dir, "history.json")
        self.default_path = os.path.join(
            ansys_linux_path if is_linux_os() else os.path.expanduser("~"), ANSYS_VENVS
        )
        self.venv_search_path = [self.default_path]
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
                    VENV_DEFAULT_PATH: self.default_path,
                    VENV_SEARCH_PATH: [self.default_path],
                }
            }
            self._create_history_file_if_not_exist()
            self._write_config_file()

    def _create_history_file_if_not_exist(self):
        """Create Configuration file if not exist."""
        if not os.path.exists(self.history_file_path) or (
            not os.path.getsize(self.history_file_path)
        ):
            os.makedirs(os.path.dirname(self.history_file_path), exist_ok=True)
            self.history = {"path": [self.default_path]}
        else:
            self._read_history_file()

    def _read_config_file(self):
        """Read configuration file."""
        try:
            with open(self.config_file_path) as f:
                paths = json.load(f)
                self.default_path = paths["path"][VENV_DEFAULT_PATH]
                self.venv_search_path = paths["path"][VENV_SEARCH_PATH]
                self.configs = paths
        except:
            self.configs = {
                "path": {
                    VENV_DEFAULT_PATH: self.default_path,
                    VENV_SEARCH_PATH: [self.default_path],
                }
            }
            self._write_config_file()

        self._read_history_file()

    def _read_history_file(self):
        """Read Configuration file."""
        try:
            with open(self.history_file_path) as f:
                paths = json.load(f)
                # Verify it is a dictionary with a key "path"
                if "path" not in paths:
                    raise ValueError("Invalid history file")
                self.history = paths
        except:
            self.history = {"path": [self.default_path]}
            self._write_history_file()

    def rewrite_config(self, key, value):
        """Rewrite configuration file.

        Parameters
        ----------
        key : str
            key to save the configuration
        value : str
            value to save the configuration
        """
        if key == VENV_DEFAULT_PATH and value not in self.history["path"]:
            self.history["path"].append(value)
        self.configs["path"][key] = value

    def _write_config_file(self):
        """Write config json file."""
        with open(self.config_file_path, "w+") as f:
            f.write(json.dumps(self.configs, indent=4))
        self._write_history_file()
        self._read_config_file()

    def _write_history_file(self):
        """Write history json file."""
        with open(self.history_file_path, "w+") as f:
            f.write(json.dumps(self.history, indent=4))

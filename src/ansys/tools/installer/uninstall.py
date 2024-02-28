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

"""Uninstall application."""
import os
import shutil

from PySide6 import QtCore, QtGui, QtWidgets

from ansys.tools.installer.configure_json import ConfigureJson
from ansys.tools.installer.constants import ANSYS_FAVICON, ASSETS_PATH
from ansys.tools.installer.linux_functions import (
    execute_linux_command,
    get_os_version,
    is_linux_os,
)


class Uninstall(QtWidgets.QWidget):
    """Manage Virtual Environment w.r.t Python versions tab."""

    def __init__(self, parent):
        """Initialize this tab."""
        try:
            super().__init__()
            self._parent = parent
            self._parent.uninstall_window = QtWidgets.QWidget()
            uninstall_window_label = QtWidgets.QLabel()
            uninstall_window_label.setText("Do you want to uninstall the application?")
            uninstall_window_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            uninstall_window_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
            uninstall_window_label.setWordWrap(True)

            uninstall_options_layout = QtWidgets.QVBoxLayout()

            # Group 1: Configure Virtual Environment Create path
            uninstall_window_cache_remove = QtWidgets.QGroupBox("Remove:")
            uninstall_window_cache_remove_layout = QtWidgets.QVBoxLayout()
            uninstall_window_cache_remove_layout.setContentsMargins(10, 20, 10, 20)
            uninstall_window_cache_remove.setLayout(
                uninstall_window_cache_remove_layout
            )

            # venv
            uninstall_window_cache_remove_venv_layout = QtWidgets.QHBoxLayout()

            uninstall_window_cache_remove_venv_text = QtWidgets.QLabel()
            uninstall_window_cache_remove_venv_text.setText(
                "Delete virtual environment "
            )
            uninstall_window_cache_remove_venv_text.setTextFormat(
                QtCore.Qt.TextFormat.RichText
            )
            uninstall_window_cache_remove_venv_text.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft
            )

            self.uninstall_window_cache_remove_venv_checkbox = QtWidgets.QCheckBox()

            uninstall_window_cache_remove_venv_layout.addWidget(
                uninstall_window_cache_remove_venv_text
            )
            uninstall_window_cache_remove_venv_layout.addWidget(
                self.uninstall_window_cache_remove_venv_checkbox
            )

            # configs
            uninstall_window_cache_remove_configs_layout = QtWidgets.QHBoxLayout()

            uninstall_window_cache_remove_configs_text = QtWidgets.QLabel()
            uninstall_window_cache_remove_configs_text.setText("Delete configurations ")
            uninstall_window_cache_remove_configs_text.setTextFormat(
                QtCore.Qt.TextFormat.RichText
            )
            uninstall_window_cache_remove_configs_text.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignLeft
            )
            uninstall_window_cache_remove_configs_text.setWordWrap(True)

            self.uninstall_window_cache_remove_configs_checkbox = QtWidgets.QCheckBox()

            uninstall_window_cache_remove_configs_layout.addWidget(
                uninstall_window_cache_remove_configs_text
            )
            uninstall_window_cache_remove_configs_layout.addWidget(
                self.uninstall_window_cache_remove_configs_checkbox
            )

            # add layout to group
            uninstall_window_cache_remove_layout.addLayout(
                uninstall_window_cache_remove_venv_layout
            )

            uninstall_window_cache_remove_layout.addLayout(
                uninstall_window_cache_remove_configs_layout
            )

            uninstall_options_layout.addWidget(uninstall_window_cache_remove)

            uninstall_window_button_save = QtWidgets.QPushButton("Uninstall")
            uninstall_window_button_save.clicked.connect(
                lambda x: self._pop_up(
                    "Do you want to proceed uninstall?", self._uninstall
                )
            )
            uninstall_window_button_close = QtWidgets.QPushButton("Close")
            uninstall_window_button_close.clicked.connect(
                lambda x: self._pop_up("Do you want to close?", self._close_all)
            )

            uninstall_window_layout_2 = QtWidgets.QHBoxLayout()
            uninstall_window_layout_2.addWidget(uninstall_window_button_save)
            uninstall_window_layout_2.addWidget(uninstall_window_button_close)

            uninstall_window_layout = QtWidgets.QVBoxLayout()
            uninstall_window_layout.addLayout(uninstall_options_layout)
            uninstall_window_layout.addLayout(uninstall_window_layout_2)
            self._parent.uninstall_window.setLayout(uninstall_window_layout)

            self._parent.uninstall_window.setWindowTitle("Uninstall")
            self._parent.uninstall_window.setWindowIcon(QtGui.QIcon(ANSYS_FAVICON))
            self._parent.uninstall_window.setWindowFlag(
                QtCore.Qt.WindowCloseButtonHint, False
            )
            self._parent.uninstall_window.resize(500, 40)
            self._parent.uninstall_window.show()

        except Exception as e:
            self._parent.show_error(str(e))

    def _uninstall(self):

        if self.uninstall_window_cache_remove_venv_checkbox.isChecked():
            self._remove_all_venvs()

        if self.uninstall_window_cache_remove_configs_checkbox.isChecked():
            self._remove_configs()

        scirpt_path = os.path.join(ASSETS_PATH, "uninstaller_ubuntu.sh")
        if get_os_version().startswith("2"):
            execute_linux_command(f"{scirpt_path}")

        self._user_confirmation_form.close()
        self._parent.uninstall_window.close()
        self._parent.close_emit()

    def _remove_all_venvs(self):
        try:
            configure = ConfigureJson()
            script_path = "bin" if is_linux_os() else "Scripts"
            for venv_dir in configure.history["path"]:
                for venv_dir_name in os.listdir(venv_dir):
                    if os.path.isfile(
                        os.path.join(venv_dir, venv_dir_name, script_path, "activate")
                    ) or (
                        not os.path.isdir(
                            os.path.join(venv_dir, venv_dir_name, "condabin")
                        )
                        and os.path.isdir(
                            os.path.join(venv_dir, venv_dir_name, "conda-meta")
                        )
                    ):
                        print(f"removed {os.path.join(venv_dir,venv_dir_name)}")
                        shutil.rmtree(
                            os.path.join(venv_dir, venv_dir_name), ignore_errors=True
                        )
        except:
            pass

    def _remove_configs(self):
        try:
            configure = ConfigureJson()
            print(f"removed {configure.config_dir}")
            shutil.rmtree(configure.config_dir, ignore_errors=True)
        except:
            pass

    def _close_all(self):
        self._user_confirmation_form.close()
        self._parent.uninstall_window.close()

    def _pop_up(self, message, call_back):

        self._user_confirmation_form = QtWidgets.QWidget()
        _user_confirmation_label = QtWidgets.QLabel()
        _user_confirmation_label.setText(message)
        _user_confirmation_label.setOpenExternalLinks(True)
        _user_confirmation_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        _user_confirmation_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        _user_confirmation_label.setWordWrap(True)

        _user_confirmation_layout_horizontal = QtWidgets.QHBoxLayout()
        _user_confirmation_yes_button = QtWidgets.QPushButton("Yes")
        _user_confirmation_yes_button.clicked.connect(call_back)
        _user_confirmation_no_button = QtWidgets.QPushButton("No")
        _user_confirmation_no_button.clicked.connect(self._user_confirmation_form.close)
        _user_confirmation_layout = QtWidgets.QVBoxLayout()
        _user_confirmation_layout.addWidget(_user_confirmation_label)
        _user_confirmation_layout_horizontal.addWidget(_user_confirmation_yes_button)
        _user_confirmation_layout_horizontal.addWidget(_user_confirmation_no_button)
        _user_confirmation_layout.addLayout(_user_confirmation_layout_horizontal)
        self._user_confirmation_form.setLayout(_user_confirmation_layout)
        self._user_confirmation_form.setWindowTitle("Confirmation")
        icon = QtGui.QIcon(ANSYS_FAVICON)
        self._user_confirmation_form.setWindowIcon(icon)
        self._user_confirmation_form.resize(400, 40)
        self._user_confirmation_form.setWindowFlag(
            QtCore.Qt.WindowCloseButtonHint, False
        )
        self._user_confirmation_form.show()

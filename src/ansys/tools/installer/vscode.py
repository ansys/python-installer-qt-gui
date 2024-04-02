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

"""VS code launch window."""
import os

from PySide6 import QtCore, QtGui, QtWidgets

from ansys.tools.installer.constants import ANSYS_FAVICON, USER_PATH


class VSCode(QtWidgets.QWidget):
    """VS code launch window."""

    def __init__(self, parent):
        """Initialize this class."""
        try:
            super().__init__()
            self._parent = parent
            if self.is_vscode_installed():
                self._parent.vscode_window = QtWidgets.QWidget()
                self._parent.vscode_window.move(
                    self._parent.vscode_window.frameGeometry().center()
                )
                vscode_window_label = QtWidgets.QLabel()
                vscode_window_label.setText("Configuration")
                vscode_window_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
                vscode_window_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
                vscode_window_label.setWordWrap(True)

                vscode_layout = QtWidgets.QVBoxLayout()

                # Group 1: Configure default Virtual Environment creation path
                vscode_window_path_config = QtWidgets.QGroupBox(
                    "VS Code open directory:"
                )
                vscode_window_path_config_layout = QtWidgets.QVBoxLayout()
                vscode_window_path_config_layout.setContentsMargins(10, 20, 10, 20)
                vscode_window_path_config.setLayout(vscode_window_path_config_layout)

                # ---> Add box
                self.vscode_window_path_config_edit = QtWidgets.QLineEdit()
                self.vscode_window_path_config_edit.setText(USER_PATH)
                vscode_window_path_config_layout.addWidget(
                    self.vscode_window_path_config_edit
                )

                self.vscode_warning_text = QtWidgets.QLabel()
                self.vscode_warning_text.setAlignment(
                    QtCore.Qt.AlignmentFlag.AlignJustify
                )
                self.vscode_warning_text.setWordWrap(True)
                vscode_window_path_config_layout.addWidget(self.vscode_warning_text)

                # Finally, add all the previous widgets to the global layout
                vscode_layout.addWidget(vscode_window_path_config)

                vscode_window_button_open = QtWidgets.QPushButton("Open")
                vscode_window_button_open.clicked.connect(
                    lambda x: self._pop_up("Do you want to open?", self._open_vscode)
                )
                vscode_window_button_close = QtWidgets.QPushButton("Close")
                vscode_window_button_close.clicked.connect(
                    lambda x: self._pop_up("Do you want to close?", self._close_all)
                )

                vscode_window_layout_1 = QtWidgets.QHBoxLayout()
                vscode_window_layout_1.addWidget(vscode_window_label)
                vscode_window_layout_2 = QtWidgets.QHBoxLayout()
                vscode_window_layout_2.addWidget(vscode_window_button_open)
                vscode_window_layout_2.addWidget(vscode_window_button_close)

                vscode_window_layout = QtWidgets.QVBoxLayout()
                vscode_window_layout.addLayout(vscode_window_layout_1)
                vscode_window_layout.addLayout(vscode_layout)
                vscode_window_layout.addLayout(vscode_window_layout_2)
                self._parent.vscode_window.setLayout(vscode_window_layout)

                self._parent.vscode_window.setWindowTitle("Configuration")
                self._parent.vscode_window.setWindowIcon(QtGui.QIcon(ANSYS_FAVICON))
                self._parent.vscode_window.resize(500, 40)
                self._parent.vscode_window.show()
            else:
                msg = QtWidgets.QMessageBox()
                msg.setTextFormat(QtCore.Qt.TextFormat.RichText)
                msg.warning(
                    self,
                    "VS Code Launch Error",
                    f"Failed to launch vscode. Try reinstalling code by following this  <a href='https://code.visualstudio.com/download'>link</a>",
                )

        except Exception as e:
            self._parent.show_error(str(e))

    def _open_vscode(self):
        """Open VS code from path."""
        # handle errors
        path = self.vscode_window_path_config_edit.text().strip()
        if os.path.exists(path):
            error_msg = "echo Failed to launch vscode. Try reinstalling code by following this link https://code.visualstudio.com/download"
            self._parent.launch_cmd(f"code {path} && exit 0 || {error_msg}")

            self.user_confirmation_form.close()
            self._parent.vscode_window.close()
        else:
            self.vscode_warning_text.setText(
                f"""{path} does not exist. Provide a valid path."""
            )
            self.vscode_warning_text.setStyleSheet(
                """
                    color: rgb(255, 0, 0);
            """
            )
            self.user_confirmation_form.close()

    def _close_all(self):
        """Close all the pop-up window."""
        self.user_confirmation_form.close()
        self._parent.vscode_window.close()

    def _pop_up(self, message, call_back):
        """Launch the confirmation pop-up window."""
        self.user_confirmation_form = QtWidgets.QWidget()
        self.user_confirmation_form.move(
            self.user_confirmation_form.frameGeometry().center()
        )
        user_confirmation_label = QtWidgets.QLabel()
        user_confirmation_label.setText(message)
        user_confirmation_label.setOpenExternalLinks(True)
        user_confirmation_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
        user_confirmation_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
        user_confirmation_label.setWordWrap(True)

        user_confirmation_layout_horizontal = QtWidgets.QHBoxLayout()
        user_confirmation_yes_button = QtWidgets.QPushButton("Yes")
        user_confirmation_yes_button.clicked.connect(call_back)
        user_confirmation_no_button = QtWidgets.QPushButton("No")
        user_confirmation_no_button.clicked.connect(self.user_confirmation_form.close)
        user_confirmation_layout = QtWidgets.QVBoxLayout()
        user_confirmation_layout.addWidget(user_confirmation_label)
        user_confirmation_layout_horizontal.addWidget(user_confirmation_yes_button)
        user_confirmation_layout_horizontal.addWidget(user_confirmation_no_button)
        user_confirmation_layout.addLayout(user_confirmation_layout_horizontal)
        self.user_confirmation_form.setLayout(user_confirmation_layout)
        self.user_confirmation_form.setWindowTitle("Confirmation")
        icon = QtGui.QIcon(ANSYS_FAVICON)
        self.user_confirmation_form.setWindowIcon(icon)
        self.user_confirmation_form.resize(400, 40)
        self.user_confirmation_form.setWindowFlag(
            QtCore.Qt.WindowCloseButtonHint, False
        )
        self.user_confirmation_form.show()

    def is_vscode_installed(self):
        """Check vs code installed or Not.

        Returns:
            Boolean
        """
        try:
            return_val = os.system("code --version")
            if return_val == 0:
                return True
            else:
                return False
        except:
            return False

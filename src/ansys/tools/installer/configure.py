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

"""Configure window."""
import os

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtGui import QStandardItem, QStandardItemModel

from ansys.tools.installer.configure_json import ConfigureJson
from ansys.tools.installer.constants import (
    ANSYS_FAVICON,
    VENV_CREATE_PATH,
    VENV_SEARCH_PATH,
)


class Configure(QtWidgets.QWidget):
    """Manage Virtual Environment w.r.t Python versions tab."""

    def __init__(self, parent):
        """Initialize this tab."""
        try:
            super().__init__()
            self._parent = parent
            self.configure_json = ConfigureJson()
            self._parent.configure_window = QtWidgets.QWidget()
            configure_window_label = QtWidgets.QLabel()
            configure_window_label.setText("Configure Ansys Python Manager")
            configure_window_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            configure_window_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
            configure_window_label.setWordWrap(True)

            configure_options_layout = QtWidgets.QVBoxLayout()

            # Group 1: Configure Virtual Environment Create path
            configure_window_create_venv = QtWidgets.QGroupBox(
                "Configure Virtual Environment Create path:"
            )
            configure_window_create_venv_layout = QtWidgets.QVBoxLayout()
            configure_window_create_venv_layout.setContentsMargins(10, 20, 10, 20)
            configure_window_create_venv.setLayout(configure_window_create_venv_layout)

            # ---> Add label
            configure_window_create_venv_text = QtWidgets.QLabel()
            configure_window_create_venv_text.setText("PATH")
            configure_window_create_venv_text.setTextFormat(
                QtCore.Qt.TextFormat.RichText
            )
            configure_window_create_venv_text.setAlignment(
                QtCore.Qt.AlignmentFlag.AlignJustify
            )
            configure_window_create_venv_text.setWordWrap(True)
            configure_window_create_venv_layout.addWidget(
                configure_window_create_venv_text
            )

            # ---> Add box
            self.configure_window_create_venv_edit = QtWidgets.QLineEdit()
            self.configure_window_create_venv_edit.setText(
                self.configure_json.default_path
            )
            configure_window_create_venv_layout.addWidget(
                self.configure_window_create_venv_edit
            )

            # Finally, add all the previous widgets to the global layout
            configure_options_layout.addWidget(configure_window_create_venv)

            # Group 2: Configure Virtual Environment Search path:
            configure_window_search_venv = QtWidgets.QGroupBox(
                "Configure Virtual Environment Search directory:"
            )
            configure_window_search_venv_layout = QtWidgets.QVBoxLayout()
            configure_window_search_venv_layout.setContentsMargins(10, 20, 10, 20)
            configure_window_search_venv.setLayout(configure_window_search_venv_layout)

            # ---> Add text
            self.configure_window_search_venv_combo = QtWidgets.QComboBox()
            self.configure_window_search_venv_model = QStandardItemModel()
            self._add_elments_to_search_configure()
            self.configure_window_search_venv_combo.currentTextChanged.connect(
                lambda x: self._change_text_search_venv()
            )
            configure_window_search_venv_layout.addWidget(
                self.configure_window_search_venv_combo
            )

            # ---> Add box
            configure_window_search_venv_Hlayout = QtWidgets.QHBoxLayout()
            self.configure_window_search_venv_edit = QtWidgets.QLineEdit()
            configure_window_search_venv_Hlayout.addWidget(
                self.configure_window_search_venv_edit
            )

            configure_window_search_venv_add = QtWidgets.QPushButton("Add")
            configure_window_search_venv_add.clicked.connect(
                lambda x: self._add_search_env()
            )
            configure_window_search_venv_Hlayout.addWidget(
                configure_window_search_venv_add
            )

            configure_window_search_venv_remove = QtWidgets.QPushButton("Remove")
            configure_window_search_venv_remove.clicked.connect(self._remove_search_env)
            configure_window_search_venv_Hlayout.addWidget(
                configure_window_search_venv_remove
            )

            configure_window_search_venv_layout.addLayout(
                configure_window_search_venv_Hlayout
            )

            # Finally, add all the previous widgets to the global layout
            configure_options_layout.addWidget(configure_window_search_venv)

            configure_window_button_save = QtWidgets.QPushButton("Save")
            configure_window_button_save.clicked.connect(
                lambda x: self._pop_up("Do you want to save?", self._save_configuration)
            )
            configure_window_button_close = QtWidgets.QPushButton("Close")
            configure_window_button_close.clicked.connect(
                lambda x: self._pop_up("Do you want to close?", self._close_all)
            )

            configure_window_layout_1 = QtWidgets.QHBoxLayout()
            configure_window_layout_1.addWidget(configure_window_label)
            configure_window_layout_2 = QtWidgets.QHBoxLayout()
            configure_window_layout_2.addWidget(configure_window_button_save)
            configure_window_layout_2.addWidget(configure_window_button_close)

            configure_window_layout = QtWidgets.QVBoxLayout()
            configure_window_layout.addLayout(configure_window_layout_1)
            configure_window_layout.addLayout(configure_options_layout)
            configure_window_layout.addLayout(configure_window_layout_2)
            self._parent.configure_window.setLayout(configure_window_layout)

            self._parent.configure_window.setWindowTitle("Configuration")
            self._parent.configure_window.setWindowIcon(QtGui.QIcon(ANSYS_FAVICON))
            self._parent.configure_window.setWindowFlag(
                QtCore.Qt.WindowCloseButtonHint, False
            )
            self._parent.configure_window.resize(500, 40)
            self._parent.configure_window.show()

        except Exception as e:
            self._parent.show_error(str(e))

    def _add_elments_to_search_configure(self):
        for x in self.configure_json.venv_search_path:
            self.configure_window_search_venv_model.appendRow(QStandardItem(x))
        self.configure_window_search_venv_combo.setModel(
            self.configure_window_search_venv_model
        )

    def _remove_search_env(self):
        if self.configure_window_search_venv_model.rowCount() <= 1:
            self._parent.show_error(
                "Minimum one path should be available to search virtual environment. Add path to remove the existing one"
            )
        elif (
            self.configure_window_search_venv_edit.text()
            == self.configure_window_create_venv_edit.text()
        ):
            self._parent.show_error(
                "Cannot delete path which is configured for default virtual environment creation."
            )
        else:
            i = 0
            removed = False
            while self.configure_window_search_venv_model.item(i):
                if (
                    self.configure_window_search_venv_model.item(i).text()
                    == self.configure_window_search_venv_edit.text()
                ):
                    self.configure_window_search_venv_model.removeRow(i)
                    self.configure_window_search_venv_combo.setModel(
                        self.configure_window_search_venv_model
                    )
                    removed = True
                i += 1
            if not removed:
                self._parent.show_error(
                    "Path is not available in the Environment search list."
                )

    def _add_search_env(self):
        if not os.path.exists(self.configure_window_search_venv_edit.text()):
            self._parent.show_error("Path not found. Create path before configure.")
        else:
            i = 0
            while self.configure_window_search_venv_model.item(i):
                if (
                    self.configure_window_search_venv_model.item(i).text()
                    == self.configure_window_search_venv_edit.text()
                ):
                    self._parent.show_error(
                        "Path is already available in the search environment list."
                    )
                    return
                i += 1
            self.configure_window_search_venv_model.appendRow(
                QStandardItem(self.configure_window_search_venv_edit.text())
            )
            self.configure_window_search_venv_combo.setModel(
                self.configure_window_search_venv_model
            )

    def _change_text_search_venv(self):
        self.configure_window_search_venv_edit.setText(
            self.configure_window_search_venv_combo.currentText()
        )

    def _save_configuration(self):
        self.configure_json.rewrite_config(
            VENV_CREATE_PATH, self.configure_window_create_venv_edit.text().strip("\\")
        )
        i = 0
        venv_search_paths = []
        while self.configure_window_search_venv_model.item(i):
            venv_search_paths.append(
                self.configure_window_search_venv_model.item(i).text().strip("\\")
            )
            i += 1
        if (
            self.configure_window_create_venv_edit.text().strip("\\")
            not in venv_search_paths
        ):
            venv_search_paths.append(
                self.configure_window_create_venv_edit.text().strip("\\")
            )
        self.configure_json.rewrite_config(VENV_SEARCH_PATH, venv_search_paths)
        i = 0

        self.configure_json._write_config_file()
        self._parent.venv_table_tab.update_table()

        self._user_confirmation_form.close()
        self._parent.configure_window.close()

    def _close_all(self):
        self._user_confirmation_form.close()
        self._parent.configure_window.close()

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

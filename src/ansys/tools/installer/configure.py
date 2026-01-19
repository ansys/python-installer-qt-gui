# Copyright (C) 2023 - 2026 ANSYS, Inc. and/or its affiliates.
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
    VENV_DEFAULT_PATH,
    VENV_SEARCH_PATH,
)


class Configure(QtWidgets.QWidget):
    """Configure tab."""

    def __init__(self, parent):
        """Initialize this class."""
        try:
            super().__init__()
            self._parent = parent
            self.configure_json = ConfigureJson()
            self._parent.configure_window = QtWidgets.QWidget()
            self._parent.configure_window.move(
                self._parent.configure_window.frameGeometry().center()
            )
            configure_window_label = QtWidgets.QLabel()
            configure_window_label.setText("Configuration")
            configure_window_label.setTextFormat(QtCore.Qt.TextFormat.RichText)
            configure_window_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignJustify)
            configure_window_label.setWordWrap(True)

            configure_options_layout = QtWidgets.QVBoxLayout()

            # Group 1: Configure default Virtual Environment creation path
            configure_window_create_venv = QtWidgets.QGroupBox(
                "Default virtual environment creation path:"
            )
            configure_window_create_venv_layout = QtWidgets.QVBoxLayout()
            configure_window_create_venv_layout.setContentsMargins(10, 20, 10, 20)
            configure_window_create_venv.setLayout(configure_window_create_venv_layout)

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
                "Locations to search for virtual environments:"
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
        """Add paths to dropdown based on configure json file."""
        for x in self.configure_json.venv_search_path:
            self.configure_window_search_venv_model.appendRow(QStandardItem(x))
        self.configure_window_search_venv_combo.setModel(
            self.configure_window_search_venv_model
        )

    def _remove_search_env(self):
        """Remove env path to the drop down."""
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
                    "Path is not available in the environment search list."
                )

    def _add_search_env(self):
        """Add env path to the drop down."""
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
        """Change the venv text bsed on the drop down."""
        self.configure_window_search_venv_edit.setText(
            self.configure_window_search_venv_combo.currentText()
        )

    def _save_configuration(self):
        """Save the configuration."""
        self.configure_json.rewrite_config(
            VENV_DEFAULT_PATH, self.configure_window_create_venv_edit.text().strip("\\")
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

        self.user_confirmation_form.close()
        self._parent.configure_window.close()

    def _close_all(self):
        """Close all the pop-up window."""
        self.user_confirmation_form.close()
        self._parent.configure_window.close()

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

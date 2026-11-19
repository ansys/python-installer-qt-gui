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

"""Native Qt installation, server and coding-agent controls for PyAnsys MCPs."""

import json
import os
from pathlib import Path
import sys
import tempfile
import time

from PySide6 import QtCore, QtGui, QtWidgets
from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from ansys.tools.installer.installed_table import DataComboBox
from ansys.tools.installer.mcp_backend import (
    application_directory,
    atomic_write,
    available_versions,
    console_executable,
    installed_version,
    package_requirement,
    prepare_installation,
    python_executable,
    read_settings,
    server_arguments,
)
from ansys.tools.installer.mcp_catalog import PRODUCTS
from ansys.tools.installer.mcp_compatibility import check_compatibility
from ansys.tools.installer.mcp_launch import launch_options, option_arguments
from ansys.tools.installer.mcp_process import CommandQueue, McpServer
from ansys.tools.installer.mcp_profiles import (
    CLIENTS,
    default_profile_path,
    render_profile,
    save_profile,
)


class _Signals(QtCore.QObject):
    completed = QtCore.Signal(object, object)
    finished = QtCore.Signal(object)


class _Task(QtCore.QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = _Signals()

    def run(self):
        try:
            self.signals.completed.emit(self.function(), None)
        except Exception as error:
            self.signals.completed.emit(None, str(error))
        finally:
            self.signals.finished.emit(self)


class _ReleaseCombo(QtWidgets.QComboBox):
    requested = QtCore.Signal()

    def showPopup(self):
        self.requested.emit()
        super().showPopup()


class McpTab(QtWidgets.QWidget):
    """Manage independently installed PyAnsys MCP servers and client profiles."""

    def __init__(self, parent=None, directory=None):
        """Build the tab without fetching metadata or installing packages on startup."""
        super().__init__(parent)
        self._manager = parent
        self.directory = Path(directory) if directory else application_directory()
        self.settings_path = self.directory / "settings.json"
        self._settings_error = None
        try:
            self.settings = read_settings(self.settings_path)
        except (OSError, ValueError) as error:
            self.settings = {}
            self._settings_error = str(error)
        self._selected = None
        self._loading = False
        self._preparing = False
        self._prepare_cancelled = False
        self._closed = False
        self._tasks = []
        self._versions = {}
        self._version_pending = set()
        self._discovery_pending = False
        self._discovered = False
        self._launch_schema = []
        self._launch_values = {}
        self._launch_context = None
        self._launch_pending = set()
        self._wheelhouse = None
        self._profile_preview = None
        self._compatibility = None
        self._compatibility_revision = 0
        self._compatibility_pending = False
        self._compatibility_error = ""
        self._probe_cache = {}
        self._manual_pythons = set()
        self._manual_environments = set()
        self._compatibility_timer = QtCore.QTimer(self)
        self._compatibility_timer.setSingleShot(True)
        self._compatibility_timer.setInterval(350)
        self._compatibility_timer.timeout.connect(self._check_compatibility)
        self._logs = {product.key: "" for product in PRODUCTS}
        self.servers = {product.key: McpServer(self) for product in PRODUCTS}
        for key, server in self.servers.items():
            server.output.connect(
                lambda message, key=key: self._append_log(key, message)
            )
            server.changed.connect(lambda _state, key=key: self._server_changed(key))
        self.queue = CommandQueue(self)
        self.queue.output.connect(
            lambda message: self._append_log(self.product.key, message)
        )
        self.queue.completed.connect(self._installed)
        self._build()
        self.product_select.currentIndexChanged.connect(self._select_product)
        self._select_product(0)
        if self._settings_error:
            self._error(f"Could not read {self.settings_path}: {self._settings_error}")
        QtWidgets.QApplication.instance().aboutToQuit.connect(self.shutdown)

    @property
    def product(self):
        """Return the selected catalog entry."""
        return PRODUCTS[self.product_select.currentIndex()]

    @property
    def environment(self):
        """Return a selected existing environment or the product's managed venv."""
        if self._custom_environment():
            value = self.environment_select.active_path
            if not value:
                raise ValueError("Choose an available virtual environment.")
            if value == "None":
                raise ValueError(
                    "No virtual environment found. Create one in Create virtual environments."
                )
            return self._environment_root(value)
        return self.directory / "environments" / self.product.key

    def _custom_environment(self):
        return self.environment_mode.currentData() == "existing"

    @staticmethod
    def _environment_root(value):
        root = Path(value).expanduser().absolute()
        return root.parent if root.name in ("Scripts", "bin") else root

    def _base_python(self):
        value = self.python_select.active_path
        return self._python_choice(value) if value and value != "None" else ""

    @staticmethod
    def _python_choice(value):
        path = Path(value).expanduser().absolute()
        if path.is_dir():
            return str(python_executable(path))
        name = path.name.lower()
        if (
            name.endswith(".exe")
            or name in ("python", "python3")
            or name.startswith("python3.")
        ):
            return str(path)
        return str(python_executable(path))

    def _button(self, text, callback):
        button = QtWidgets.QPushButton(text)
        button.clicked.connect(lambda: self._try(callback))
        return button

    def _field_with_browse(self, field, callback):
        widget = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(field, 1)
        row.addWidget(self._button("Browse…", callback))
        return widget

    def _page(self, tabs, title):
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        page = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(page)
        scroll.setWidget(page)
        tabs.addTab(scroll, title)
        return layout

    @staticmethod
    def _label(text=""):
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setTextFormat(QtCore.Qt.PlainText)
        return label

    @staticmethod
    def _compact_combo(combo):
        combo.setSizeAdjustPolicy(
            QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        combo.setMinimumContentsLength(20)
        combo.setMinimumWidth(0)
        combo.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        return combo

    def _section(self, title, parent_layout):
        section = QtWidgets.QGroupBox(title)
        section.setProperty("mcpSection", True)
        contents = QtWidgets.QVBoxLayout(section)
        contents.setContentsMargins(12, 18, 12, 12)
        contents.setSpacing(8)
        parent_layout.addWidget(section)
        return section, contents

    @staticmethod
    def _form(layout):
        form = QtWidgets.QFormLayout()
        form.setFieldGrowthPolicy(QtWidgets.QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QtWidgets.QFormLayout.WrapLongRows)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        layout.addLayout(form)
        return form

    def _fold(self, title, parent_layout):
        toggle = QtWidgets.QToolButton()
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        toggle.setArrowType(QtCore.Qt.RightArrow)
        parent_layout.addWidget(toggle)
        body = QtWidgets.QWidget()
        contents = QtWidgets.QVBoxLayout(body)
        contents.setContentsMargins(12, 4, 0, 8)
        contents.setSpacing(8)
        body.hide()
        parent_layout.addWidget(body)
        toggle.toggled.connect(body.setVisible)
        toggle.toggled.connect(
            lambda expanded: toggle.setArrowType(
                QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
            )
        )
        return toggle, body, contents

    def _build(self):
        self.setStyleSheet("""
            QGroupBox[mcpSection="true"] {
                border: 1px solid palette(mid); border-radius: 5px;
                margin-top: 10px;
            }
            QGroupBox[mcpSection="true"]::title {
                subcontrol-origin: margin; left: 10px; padding: 0 4px;
                font-weight: 600;
            }
            QComboBox, QLineEdit, QSpinBox { min-height: 26px; }
            QPushButton { min-height: 28px; padding: 0 10px; }
            QPushButton[primary="true"] { font-weight: 600; }
        """)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)
        _header, header = self._section("MCP product", layout)
        row = QtWidgets.QHBoxLayout()
        self.product_select = self._compact_combo(QtWidgets.QComboBox())
        self.product_select.setAccessibleName("PyAnsys MCP product")
        self.product_select.addItems([product.name for product in PRODUCTS])
        row.addWidget(self.product_select, 1)
        self.installed_label = self._label()
        row.addWidget(self.installed_label)
        header.addLayout(row)
        description_row = QtWidgets.QHBoxLayout()
        self.description = self._label()
        description_row.addWidget(self.description, 1)
        self.guide = QtWidgets.QLabel()
        self.guide.setOpenExternalLinks(True)
        description_row.addWidget(self.guide)
        header.addLayout(description_row)
        self.pages = QtWidgets.QTabWidget()
        layout.addWidget(self.pages, 1)
        self._setup_page()
        self._server_page()
        self._client_page()
        self.action_stack = QtWidgets.QStackedWidget()
        for actions in (self.install_actions, self.server_actions, self.client_actions):
            self.action_stack.addWidget(actions)
        layout.addWidget(self.action_stack)
        self.pages.currentChanged.connect(self.action_stack.setCurrentIndex)
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        layout.addWidget(self.progress)
        self.status = self._label("Select an MCP and an environment to get started.")
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.log_group = QtWidgets.QToolButton()
        self.log_group.setText("Activity log")
        self.log_group.setCheckable(True)
        self.log_group.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.log_group.setArrowType(QtCore.Qt.RightArrow)
        layout.addWidget(self.log_group)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setAccessibleName("Installation and server log")
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setMaximumHeight(145)
        self.log.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.log.hide()
        layout.addWidget(self.log)
        self.log_group.toggled.connect(self.log.setVisible)
        self.log_group.toggled.connect(
            lambda expanded: self.log_group.setArrowType(
                QtCore.Qt.DownArrow if expanded else QtCore.Qt.RightArrow
            )
        )

    def _setup_page(self):
        layout = self._page(self.pages, "Installation")
        layout.setSpacing(10)
        self.install_options = QtWidgets.QWidget()
        options = QtWidgets.QVBoxLayout(self.install_options)
        options.setContentsMargins(0, 0, 0, 0)
        options.setSpacing(10)
        self.environment_section, environment = self._section(
            "Python environment", options
        )
        mode_row = QtWidgets.QHBoxLayout()
        self.environment_mode = self._compact_combo(QtWidgets.QComboBox())
        self.environment_mode.setAccessibleName("Installation environment")
        self.environment_mode.addItem("Dedicated environment (recommended)", "managed")
        self.environment_mode.addItem("Existing virtual environment", "existing")
        mode_row.addWidget(self.environment_mode, 1)
        self.refresh_choices_button = self._button("Refresh", self._refresh_choices)
        self.refresh_choices_button.setToolTip(
            "Refresh the Python and virtual environments discovered by APM."
        )
        mode_row.addWidget(self.refresh_choices_button)
        environment.addLayout(mode_row)
        self.managed_panel = QtWidgets.QWidget()
        managed = QtWidgets.QVBoxLayout(self.managed_panel)
        managed.setContentsMargins(0, 0, 0, 0)
        managed.setSpacing(4)
        self.python_caption = self._label("Select Python version")
        managed.addWidget(self.python_caption)
        self.python_select = self._compact_combo(
            DataComboBox(
                installed_python=True, installed_forge=True, populate_on_init=False
            )
        )
        self.python_select.setAccessibleName("Select Python version")
        managed.addWidget(self.python_select)
        self.managed_python_info = self._label()
        managed.addWidget(self.managed_python_info)
        environment.addWidget(self.managed_panel)
        self.existing_panel = QtWidgets.QWidget()
        existing = QtWidgets.QVBoxLayout(self.existing_panel)
        existing.setContentsMargins(0, 0, 0, 0)
        existing.setSpacing(4)
        existing.addWidget(self._label("Available virtual environments"))
        self.environment_select = self._compact_combo(
            DataComboBox(created_venv=True, populate_on_init=False)
        )
        self.environment_select.setAccessibleName("Available virtual environments")
        existing.addWidget(self.environment_select)
        environment.addWidget(self.existing_panel)
        self.python_hint = self._label()
        support = self._form(environment)
        self.python_support = self._label()
        support.addRow("Supported Python", self.python_support)
        environment.addWidget(self.python_hint)
        self.package_section, package = self._section("MCP package", options)
        self.package_form = self._form(package)
        self.source = self._compact_combo(QtWidgets.QComboBox())
        self.source.addItem("PyPI release", "release")
        self.source.addItem("Official Git repository", "branch")
        self.source.addItem("Offline wheelhouse", "offline")
        self.package_form.addRow("Install from", self.source)
        self.version = _ReleaseCombo()
        self.version.requested.connect(self._fetch_versions)
        self.version.setEditable(True)
        self.version.addItem("Latest", "")
        self.version.setToolTip("Latest is resolved again on every installation.")
        self.version_row = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(self.version_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.version, 1)
        self.package_form.addRow("Version", self.version_row)
        self.branch = QtWidgets.QLineEdit("main")
        self.package_form.addRow("Branch / tag", self.branch)
        self.wheelhouse_path = QtWidgets.QLineEdit()
        self.wheelhouse_path.setPlaceholderText("Select a wheel folder or ZIP")
        self.wheelhouse_row = self._field_with_browse(
            self.wheelhouse_path, self._browse_wheelhouse
        )
        self.package_form.addRow("Wheelhouse", self.wheelhouse_row)
        self.source_hint = self._label()
        package.addWidget(self.source_hint)
        self.install_advanced_toggle, self.install_advanced, advanced = self._fold(
            "Other locations and details", options
        )
        self.location_details = self._label()
        self.location_details.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        advanced.addWidget(self.location_details)
        manual = QtWidgets.QHBoxLayout()
        manual.addWidget(self._button("Add Python executable…", self._browse_python))
        manual.addWidget(
            self._button("Add virtual environment…", self._browse_environment)
        )
        advanced.addLayout(manual)
        layout.addWidget(self.install_options)
        layout.addStretch()
        self.install_actions = QtWidgets.QWidget()
        buttons = QtWidgets.QHBoxLayout(self.install_actions)
        buttons.setContentsMargins(0, 0, 0, 0)
        self.save_button = self._button("Save settings", self._save)
        buttons.addWidget(self.save_button)
        buttons.addStretch()
        self.cancel_button = self._button("Cancel", self._cancel_install)
        buttons.addWidget(self.cancel_button)
        self.install_button = self._button("Install MCP", lambda: self._install(True))
        self.install_button.setProperty("primary", True)
        buttons.addWidget(self.install_button)
        self.environment_mode.currentIndexChanged.connect(self._options_changed)
        for combo in (self.python_select, self.environment_select):
            combo.currentIndexChanged.connect(self._options_changed)
        self.source.currentIndexChanged.connect(self._requirements_changed)
        self.version.currentTextChanged.connect(self._requirements_changed)
        self.branch.textChanged.connect(self._requirements_changed)
        self.wheelhouse_path.textChanged.connect(self._requirements_changed)

    def _server_page(self):
        layout = self._page(self.pages, "Server settings")
        layout.setSpacing(10)
        layout.addWidget(
            self._label(
                "For a coding agent on this computer, use the automatic connection in Coding agents. Start HTTP here when you need a shared server."
            )
        )
        self.server_options = QtWidgets.QWidget()
        options = QtWidgets.QVBoxLayout(self.server_options)
        options.setContentsMargins(0, 0, 0, 0)
        options.setSpacing(10)
        self.http_section, http = self._section("Local HTTP server", options)
        form = self._form(http)
        self.http_port = QtWidgets.QSpinBox()
        self.http_port.setRange(1, 65535)
        form.addRow("HTTP port", self.http_port)
        self.endpoint = self._label()
        self.endpoint.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        http.addWidget(self.endpoint)
        self.server_status = self._label()
        http.addWidget(self.server_status)
        http.addWidget(
            self._label(
                "Available on this computer only. APM stops its servers when it closes."
            )
        )
        self.stdio_notice, stdio = self._section("Automatic server", options)
        stdio.addWidget(
            self._label(
                "This MCP uses stdio. Your coding agent starts and stops it automatically."
            )
        )
        stdio.addWidget(
            self._button("Set up coding agent", lambda: self.pages.setCurrentIndex(2))
        )
        self.solver_section, solver = self._section("Solver connection", options)
        self.connect = QtWidgets.QCheckBox("Connect to a running solver on startup")
        solver.addWidget(self.connect)
        self.solver_fields = QtWidgets.QWidget()
        solver_form = self._form(QtWidgets.QVBoxLayout(self.solver_fields))
        self.machine = QtWidgets.QLineEdit("127.0.0.1")
        solver_form.addRow("Solver host", self.machine)
        self.solver_port = QtWidgets.QSpinBox()
        self.solver_port.setRange(1, 65535)
        solver_form.addRow("Solver port", self.solver_port)
        solver.addWidget(self.solver_fields)
        self.server_advanced_toggle, self.server_advanced, advanced = self._fold(
            "Advanced launch settings", options
        )
        advanced.addWidget(
            self._label(
                "Applies to HTTP servers and automatic coding-agent connections."
            )
        )
        self.aedt_section, aedt = self._section("PyAEDT options", advanced)
        self.graphical = QtWidgets.QCheckBox("Open the AEDT graphical interface")
        self.context = QtWidgets.QCheckBox("Include AEDT context tools")
        self.dynamic = QtWidgets.QCheckBox("Enable dynamic tool discovery")
        for field in (self.graphical, self.context, self.dynamic):
            aedt.addWidget(field)
        _launch, launch = self._section("Available launch options", advanced)
        self.launch_hint = self._label(
            "Expand advanced settings to read options from the installed MCP."
        )
        launch.addWidget(self.launch_hint)
        self.launch_choice = self._compact_combo(QtWidgets.QComboBox())
        self.launch_choice.setAccessibleName("Add launch option")
        launch.addWidget(self.launch_choice)
        self.launch_rows = QtWidgets.QVBoxLayout()
        launch.addLayout(self.launch_rows)
        self.launch_choice.activated.connect(self._add_launch_option)
        self.server_advanced_toggle.toggled.connect(
            lambda expanded: self._load_launch_options() if expanded else None
        )
        self.raw_arguments_toggle, _raw, raw = self._fold("Custom arguments", advanced)
        raw.addWidget(
            self._label(
                "For expert use. Prefer the available options above. Enter a JSON array with each option and value as a separate string."
            )
        )
        self.extra = QtWidgets.QPlainTextEdit("[]")
        self.extra.setAccessibleName("Additional launch arguments")
        self.extra.setMaximumHeight(75)
        raw.addWidget(self.extra)
        _variables, variables = self._section("Environment variables", advanced)
        variables.addWidget(
            self._label(
                'JSON object, for example {"NAME": "value"}. Values are saved as plain text.'
            )
        )
        self.environment_json = QtWidgets.QPlainTextEdit("{}")
        self.environment_json.setAccessibleName("Environment variables")
        self.environment_json.setMaximumHeight(75)
        variables.addWidget(self.environment_json)
        layout.addWidget(self.server_options)
        layout.addStretch()
        self.server_actions = QtWidgets.QWidget()
        actions = QtWidgets.QVBoxLayout(self.server_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        buttons = QtWidgets.QHBoxLayout()
        self.server_save_button = self._button("Save settings", self._save)
        buttons.addWidget(self.server_save_button)
        buttons.addStretch()
        self.stop_button = self._button(
            "Stop server", lambda: self.servers[self.product.key].stop()
        )
        buttons.addWidget(self.stop_button)
        self.start_button = self._button("Start HTTP server", self._start_server)
        self.start_button.setProperty("primary", True)
        buttons.addWidget(self.start_button)
        actions.addLayout(buttons)
        self.connect.toggled.connect(self._options_changed)
        self.http_port.valueChanged.connect(self._options_changed)

    def _client_page(self):
        layout = self._page(self.pages, "Coding agents")
        layout.setSpacing(10)
        self.client_section, client = self._section("Agent connection", layout)
        form = self._form(client)
        self.client = self._compact_combo(QtWidgets.QComboBox())
        self.client.addItems(CLIENTS)
        form.addRow("Coding agent", self.client)
        self.transport = self._compact_combo(QtWidgets.QComboBox())
        form.addRow("Connection", self.transport)
        self.client_hint = self._label()
        client.addWidget(self.client_hint)
        self.profile_section, profile = self._section("Configuration file", layout)
        self.vscode_format = self._compact_combo(QtWidgets.QComboBox())
        self.vscode_format.addItem("Copilot harness (current)", False)
        self.vscode_format.addItem("Local harness (legacy)", True)
        self.vscode_format.setAccessibleName("VS Code configuration format")
        profile.addWidget(self.vscode_format)
        self.profile_path = QtWidgets.QLineEdit()
        self.profile_path.setAccessibleName("Coding agent configuration file")
        profile.addWidget(
            self._field_with_browse(self.profile_path, self._browse_profile)
        )
        self.profile_hint = self._label()
        profile.addWidget(self.profile_hint)
        self.workspace_button = self._button(
            "Choose workspace…", self._browse_workspace
        )
        profile.addWidget(self.workspace_button)
        self.preview_section, preview = self._section("Review configuration", layout)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setAccessibleName("Configuration preview")
        self.preview.setFont(
            QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
        )
        self.preview.setMinimumHeight(130)
        preview.addWidget(self.preview)
        self.preview_section.hide()
        layout.addStretch()
        self.client_actions = QtWidgets.QWidget()
        buttons = QtWidgets.QHBoxLayout(self.client_actions)
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.addStretch()
        self.write_profile_button = self._button(
            "Review configuration…", self._review_or_write_profile
        )
        self.write_profile_button.setProperty("primary", True)
        buttons.addWidget(self.write_profile_button)
        self.client.currentTextChanged.connect(self._client_changed)
        self.transport.currentIndexChanged.connect(self._connection_changed)
        self.profile_path.textChanged.connect(self._invalidate_preview)
        self.vscode_format.currentIndexChanged.connect(self._vscode_format_changed)
        self.http_port.valueChanged.connect(self._invalidate_preview)
        self.extra.textChanged.connect(self._launch_options_changed)
        self.environment_json.textChanged.connect(self._launch_options_changed)
        for field in (self.connect, self.graphical, self.context, self.dynamic):
            field.toggled.connect(self._launch_options_changed)
        self.machine.textChanged.connect(self._invalidate_preview)
        self.solver_port.valueChanged.connect(self._invalidate_preview)
        self._client_changed()

    def _try(self, action):
        try:
            action()
        except Exception as error:
            self._error(str(error))

    def _error(self, message):
        self.status.setText(message)
        self._append_log(self.product.key, f"\nError: {message}\n")
        self.log_group.setChecked(True)

    def _append_log(self, key, message):
        self._logs[key] = (self._logs[key] + message)[-150000:]
        if self.product.key == key:
            self.log.moveCursor(QtGui.QTextCursor.End)
            self.log.insertPlainText(message)
            self.log.moveCursor(QtGui.QTextCursor.End)

    def _select_product(self, index):
        if self._selected is not None:
            try:
                self._save(self._selected, announce=False)
            except (OSError, ValueError) as error:
                self.product_select.blockSignals(True)
                self.product_select.setCurrentIndex(self._selected)
                self.product_select.blockSignals(False)
                self._error(str(error))
                return
        self._selected = index
        self._loading = True
        product = self.product
        values = self.settings.get(product.key, {})
        self.description.setText(product.description)
        self.guide.setText(f'<a href="{product.documentation}">Documentation ↗</a>')
        selected_python = str(values.get("base_python", self._base_python()))
        if (
            not selected_python
            and self._manager is not None
            and hasattr(self._manager, "venv_table_tab")
        ):
            path = self._manager.venv_table_tab.table.active_path
            if path and path != "None":
                selected_python = self._python_choice(path)
        if not selected_python and not getattr(sys, "frozen", False):
            selected_python = sys.executable
        if selected_python:
            self.select_python(selected_python)
        selected_environment = str(values.get("environment", ""))
        if selected_environment:
            self._manual_environments.add(selected_environment)
            self._select_path(self.environment_select, selected_environment)
        self.environment_mode.setCurrentIndex(
            1 if values.get("custom", False) is True else 0
        )
        self.source.setCurrentIndex(
            2
            if values.get("offline", False) is True
            else 1 if values.get("source") == "branch" else 0
        )
        self.version.clear()
        self.version.addItem("Latest", "")
        version = str(values.get("version", ""))
        if version:
            self.version.addItem(version, version)
            self.version.setCurrentIndex(1)
        self.branch.setText(str(values.get("branch", "main")))
        self.wheelhouse_path.setText(str(values.get("wheelhouse", "")))
        self.http_port.setValue(self._port(values.get("http_port"), 8080 + index))
        self.solver_port.setValue(
            self._port(values.get("solver_port"), product.product_port or 50051)
        )
        self.connect.setChecked(values.get("connect", False) is True)
        self.machine.setText(str(values.get("machine", "127.0.0.1")))
        self.graphical.setChecked(values.get("graphical", False) is True)
        self.context.setChecked(values.get("context", False) is True)
        self.dynamic.setChecked(values.get("dynamic", False) is True)
        self.extra.setPlainText(str(values.get("extra", "[]")))
        self._launch_values = dict(values.get("launch_options", {}))
        self._launch_schema = []
        self._launch_context = None
        self.launch_hint.setText(
            "Expand advanced settings to read options from the installed MCP."
        )
        self._render_launch_options()
        self.environment_json.setPlainText(str(values.get("env", "{}")))
        self.client.setCurrentText(str(values.get("client", self.client.currentText())))
        legacy = values.get(
            "vscode_legacy", str(values.get("profile_path", "")).endswith("mcp.json")
        )
        self.vscode_format.setCurrentIndex(1 if legacy else 0)
        self._update_transports(str(values.get("transport", "stdio")))
        if "profile_path" in values:
            self.profile_path.setText(str(values["profile_path"]))
        self.server_advanced_toggle.setChecked(False)
        self.install_advanced_toggle.setChecked(False)
        self.log.setPlainText(self._logs[product.key])
        self._loading = False
        self._requirements_changed()
        if self.isVisible():
            self._fetch_versions()

    @staticmethod
    def _port(value, default):
        return value if type(value) is int and 1 <= value <= 65535 else default

    def _version(self):
        return (
            ""
            if self.version.currentText().strip().lower()
            in ("latest", "latest compatible", "")
            else self.version.currentText().strip()
        )

    def _save(self, index=None, announce=True):
        if self._settings_error:
            raise ValueError(
                f"Repair {self.settings_path} before saving: {self._settings_error}"
            )
        index = self.product_select.currentIndex() if index is None else index
        self.settings[PRODUCTS[index].key] = {
            "base_python": self._base_python(),
            "custom": self._custom_environment(),
            "environment": self._selected_environment_path(),
            "source": "branch" if self.source.currentData() == "branch" else "release",
            "version": self._version(),
            "branch": self.branch.text().strip(),
            "offline": self.source.currentData() == "offline",
            "wheelhouse": self.wheelhouse_path.text().strip(),
            "http_port": self.http_port.value(),
            "solver_port": self.solver_port.value(),
            "connect": self.connect.isChecked(),
            "machine": self.machine.text().strip(),
            "graphical": self.graphical.isChecked(),
            "context": self.context.isChecked(),
            "dynamic": self.dynamic.isChecked(),
            "extra": self.extra.toPlainText(),
            "launch_options": dict(self._launch_values),
            "env": self.environment_json.toPlainText(),
            "client": self.client.currentText(),
            "vscode_legacy": self.vscode_format.currentData(),
            "profile_path": self.profile_path.text().strip(),
            "transport": self._transport(),
        }
        atomic_write(self.settings_path, json.dumps(self.settings, indent=2) + "\n")
        if announce:
            self.status.setText("MCP settings saved.")

    def _selected_environment_path(self):
        value = self.environment_select.active_path
        return str(self._environment_root(value)) if value and value != "None" else ""

    @staticmethod
    def _same_path(left, right):
        return os.path.normcase(os.path.abspath(left)) == os.path.normcase(
            os.path.abspath(right)
        )

    def _choice_executable(self, combo, index):
        data = combo.itemData(index) or {}
        value = data.get("path", "")
        if not value or value == "None":
            return ""
        if combo is self.environment_select:
            value = self._environment_root(value)
        return (
            str(python_executable(value))
            if combo is self.environment_select
            else self._python_choice(value)
        )

    def _select_path(self, combo, value):
        target = (
            self._python_choice(value)
            if combo is self.python_select
            else str(self._environment_root(value))
        )
        for index in range(combo.count()):
            data = combo.itemData(index) or {}
            path = data.get("path", "")
            if not path or path == "None":
                continue
            candidate = (
                self._python_choice(path)
                if combo is self.python_select
                else str(self._environment_root(path))
            )
            if self._same_path(candidate, target):
                combo.setCurrentIndex(index)
                return
        label = (
            f"Python — {target}"
            if combo is self.python_select
            else f"{Path(target).name} — {target}"
        )
        combo.addItem(
            label,
            {
                "path": target,
                "version": (
                    "Python" if combo is self.python_select else Path(target).name
                ),
                "admin": "False",
            },
        )
        combo.setItemData(combo.count() - 1, target, QtCore.Qt.ToolTipRole)
        combo.setCurrentIndex(combo.count() - 1)

    def select_python(self, executable):
        """Select an interpreter using the same discovered choices as Create environments."""
        self._manual_pythons.add(str(executable))
        self._select_path(self.python_select, executable)
        self._requirements_changed()

    def select_environment(self, directory):
        """Select an existing environment from APM's shared environment dropdown."""
        self._manual_environments.add(str(directory))
        self._select_path(self.environment_select, directory)
        self.environment_mode.setCurrentIndex(1)
        self._requirements_changed()

    def _apply_choices(self, snapshots):
        preferred = (self._base_python(), self._selected_environment_path())
        self._loading = True
        for combo, entries, manual, selected in zip(
            (self.python_select, self.environment_select),
            snapshots,
            (self._manual_pythons, self._manual_environments),
            preferred,
        ):
            with QtCore.QSignalBlocker(combo):
                combo.set_entries(entries)
                for value in sorted(manual):
                    self._select_path(combo, value)
                if selected:
                    self._select_path(combo, selected)
        self._loading = False
        self._discovered = True
        self._requirements_changed()

    def _refresh_choices(self):
        if (
            self.queue.active
            or self._preparing
            or self._closed
            or self._discovery_pending
        ):
            return
        self._discovery_pending = True
        self.refresh_choices_button.setEnabled(False)
        self._background(
            lambda: (self.python_select.discover(), self.environment_select.discover()),
            self._choices_discovered,
        )

    @QtCore.Slot(object, object)
    def _choices_discovered(self, snapshots, error):
        self._discovery_pending = False
        if self._closed:
            return
        self.refresh_choices_button.setEnabled(True)
        if error:
            self._error(f"Could not refresh environments: {error}")
        else:
            self._launch_context = None
            self._apply_choices(snapshots)
            if self.server_advanced_toggle.isChecked():
                self._load_launch_options()

    def showEvent(self, event):
        """Reuse APM's discovery snapshots; never run subprocesses on tab selection."""
        super().showEvent(event)
        manager = self._manager
        if manager is not None and hasattr(manager, "installed_table_tab"):
            sources = (
                manager.venv_table_tab.table,
                manager.installed_table_tab.venv_table,
            )
            snapshots = tuple(
                [(combo.itemText(i), combo.itemData(i)) for i in range(combo.count())]
                for combo in sources
            )
            if snapshots != getattr(self, "_shared_choices", None):
                self._shared_choices = snapshots
                self._apply_choices(snapshots)
        elif not self._discovered:
            self._refresh_choices()
        if self._compatibility is None and not self._compatibility_pending:
            self._requirements_changed()
        self._fetch_versions()

    def _options_changed(self):
        if self._loading:
            return
        self._invalidate_preview()
        self._refresh()
        if self.server_advanced_toggle.isChecked():
            self._load_launch_options()

    def _set_choice_enabled(self, combo, index, enabled, reason=""):
        item = combo.model().item(index)
        item.setEnabled(enabled)
        item.setSelectable(enabled)
        role = QtCore.Qt.UserRole + 1
        label = combo.itemData(index, role)
        if label is None:
            label = combo.itemText(index)
            combo.setItemData(index, label, role)
        combo.setItemText(index, label if enabled else f"Unavailable · {label}")
        data = combo.itemData(index) or {}
        combo.setItemData(index, reason or data.get("path", ""), QtCore.Qt.ToolTipRole)

    def _choose_supported_python(self):
        combo = self.python_select
        if (
            combo.currentIndex() >= 0
            and combo.model().item(combo.currentIndex()).isEnabled()
        ):
            return
        with QtCore.QSignalBlocker(combo):
            combo.setCurrentIndex(
                next(
                    (
                        index
                        for index in range(combo.count())
                        if combo.model().item(index).isEnabled()
                    ),
                    -1,
                )
            )

    def _catalog_filter(self):
        for combo in (self.python_select, self.environment_select):
            for index in range(combo.count()):
                data = combo.itemData(index) or {}
                enabled = bool(self._choice_executable(combo, index))
                reason = ""
                if combo is self.python_select and data.get("version", "").startswith(
                    "Python "
                ):
                    try:
                        enabled = enabled and Version(
                            data["version"].split(" ", 1)[1]
                        ) in SpecifierSet(self.product.python)
                        if not enabled:
                            reason = f"{self.product.name} supports 64-bit Python {self.product.python}."
                    except InvalidVersion:
                        pass
                self._set_choice_enabled(combo, index, enabled, reason)
        self._choose_supported_python()

    def _requirements_changed(self, *_):
        if self._loading or self._closed:
            return
        self._compatibility_revision += 1
        self._compatibility = None
        self._compatibility_error = ""
        self._compatibility_pending = False
        self._compatibility_timer.stop()
        self._catalog_filter()
        if self.isVisible() and not self.queue.active and not self._preparing:
            self._compatibility_pending = True
            self._compatibility_timer.start()
        self._invalidate_preview()
        self._refresh()
        if self.isVisible():
            self._fetch_versions()

    def _check_compatibility(self):
        if self._closed or self.queue.active or self._preparing:
            return
        revision = self._compatibility_revision
        product = self.product
        paths = [
            self._choice_executable(combo, index)
            for combo in (self.python_select, self.environment_select)
            for index in range(combo.count())
        ]
        managed = self.directory / "environments" / product.key
        if python_executable(managed).is_file():
            paths.append(str(python_executable(managed)))
        offline = self.source.currentData() == "offline"
        options = dict(
            version=self._version(),
            source="release" if offline else self.source.currentData(),
            branch=self.branch.text().strip(),
            wheelhouse=self.wheelhouse_path.text().strip() if offline else None,
            probes=dict(self._probe_cache),
        )
        if offline and not options["wheelhouse"]:
            self._compatibility_pending = False
            self._compatibility_error = (
                "Choose a wheelhouse to check its Python requirements."
            )
            self._refresh()
            return

        def check():
            try:
                return revision, check_compatibility(product, paths, **options), ""
            except Exception as error:
                return revision, None, str(error)

        self._background(check, self._compatibility_checked)

    @QtCore.Slot(object, object)
    def _compatibility_checked(self, payload, error):
        if self._closed:
            return
        if error or payload is None:
            return
        revision, result, error = payload
        if revision != self._compatibility_revision:
            return
        self._compatibility_pending = False
        self._compatibility_error = error
        self._compatibility = result
        self.python_hint.setToolTip(error)
        if error:
            self._append_log(self.product.key, f"Compatibility check: {error}\n")
        if result is not None:
            self._probe_cache = result.probes
            for combo in (self.python_select, self.environment_select):
                for index in range(combo.count()):
                    executable = self._choice_executable(combo, index)
                    self._set_choice_enabled(
                        combo,
                        index,
                        executable in result.interpreters,
                        result.errors.get(
                            executable, "No Python interpreter was found."
                        ),
                    )
            self._choose_supported_python()
        self._refresh()

    def _python_selection_state(self):
        try:
            root = self.environment
        except ValueError:
            return (
                False,
                "Select an available environment, or create one in Create virtual environments.",
            )
        existing = python_executable(root)
        executable = (
            str(existing)
            if self._custom_environment() or existing.is_file()
            else self._base_python()
        )
        if self._compatibility_pending:
            return False, "Checking the selected release and installed Python versions…"
        if self._compatibility_error:
            if (
                self.source.currentData() == "offline"
                and not self.wheelhouse_path.text().strip()
            ):
                return False, "Choose a wheelhouse to check its Python requirements."
            return (
                bool(executable),
                "Release requirements could not be checked. Install retries before making changes; see the activity log for details.",
            )
        if self._compatibility is not None:
            release = self._compatibility.release
            required = str(
                SpecifierSet(release.requires_python)
                & SpecifierSet(self.product.python)
            )
            info = self._compatibility.interpreters.get(executable)
            if info is not None:
                if existing.is_file() and not self._custom_environment():
                    return True, f"{release.version} requires 64-bit Python {required}."
                prefix = (
                    "Dedicated environment uses"
                    if existing.is_file() and not self._custom_environment()
                    else "Selected"
                )
                return (
                    True,
                    f"{prefix} Python {info.version} (64-bit). {release.version} requires Python {required}.",
                )
            if existing.is_file() and not self._custom_environment():
                return (
                    False,
                    f"This dedicated environment is incompatible with {release.version}. Choose an existing environment with Python {required}, or create one in Create virtual environments.",
                )
            return (
                False,
                f"{release.version} requires 64-bit Python {required}. Select a supported Python or environment.",
            )
        if not executable:
            return (
                False,
                f"Install 64-bit Python {self.product.python} in Install Python, then refresh the choices here.",
            )
        return (
            True,
            f"Requires 64-bit Python {self.product.python}. The selected release is checked before installation.",
        )

    @staticmethod
    def _readable_python(specification):
        bounds = list(SpecifierSet(specification))
        if all(bound.operator in (">=", ">", "<=", "<") for bound in bounds):
            lower = [bound for bound in bounds if bound.operator.startswith(">")]
            upper = [bound for bound in bounds if bound.operator.startswith("<")]
            selected = (
                [max(lower, key=lambda bound: Version(bound.version))] if lower else []
            ) + (
                [min(upper, key=lambda bound: Version(bound.version))] if upper else []
            )
            return ", ".join(
                str(bound)
                .replace(">=", "≥ ")
                .replace("<=", "≤ ")
                .replace("<", "< ")
                .replace(">", "> ")
                for bound in selected
            )
        return specification

    def _refresh(self):
        product = self.product
        server = self.servers[product.key]
        busy = self.queue.active or self._preparing
        environment_busy, installed, managed_exists = False, False, False
        try:
            root = self.environment
            environment_busy = self.environment_in_use(root)
            version = installed_version(root, product)
            installed = console_executable(root, product).is_file() and bool(version)
            managed_exists = (
                not self._custom_environment() and python_executable(root).is_file()
            )
            self.installed_label.setText(
                f"Installed · {version}" if installed else "Not installed"
            )
            self.location_details.setText(
                f"Environment: {root}\nPython: {python_executable(root) if managed_exists else self._base_python()}"
            )
        except (ValueError, OSError) as error:
            self.installed_label.setText("Not installed")
            self.location_details.setText(str(error))
        compatible, hint = self._python_selection_state()
        for spec in sorted(
            {
                str(SpecifierSet(self.product.python)),
                (
                    str(
                        SpecifierSet(self._compatibility.release.requires_python)
                        & SpecifierSet(self.product.python)
                    )
                    if self._compatibility
                    else ""
                ),
            },
            key=len,
            reverse=True,
        ):
            if spec:
                hint = hint.replace(spec, self._readable_python(spec))
        self.python_hint.setText(hint)
        required = self.product.python
        release_name = ""
        if self._compatibility is not None:
            release = self._compatibility.release
            required = str(
                SpecifierSet(required) & SpecifierSet(release.requires_python)
            )
            release_name = f" · MCP {release.version}"
        self.python_support.setText(
            f"{self._readable_python(required)} · 64-bit{release_name}"
        )
        self.python_hint.setVisible(
            not compatible
            or self._compatibility_pending
            or bool(self._compatibility_error)
        )
        self.product_select.setEnabled(not busy)
        self.install_options.setEnabled(not busy and not server.active)
        self.install_button.setText("Update / repair" if installed else "Install MCP")
        self.install_button.setEnabled(not busy and not environment_busy and compatible)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        self.save_button.setEnabled(not busy)
        self.server_save_button.setEnabled(not busy)
        self.progress.setVisible(busy)
        self.managed_panel.setVisible(not self._custom_environment())
        self.existing_panel.setVisible(self._custom_environment())
        self.python_select.setEnabled(not managed_exists)
        self.python_select.setVisible(not managed_exists)
        self.python_caption.setText(
            "Python version" if managed_exists else "Select Python version"
        )
        self.managed_python_info.setVisible(managed_exists)
        if managed_exists:
            probe = self._probe_cache.get(str(python_executable(root)))
            self.managed_python_info.setText(
                f"Python {probe[1].version} ({probe[1].bits}-bit) · existing dedicated environment"
                if probe
                else "Checking the existing environment…"
            )
        source = self.source.currentData()
        self.package_form.setRowVisible(self.version_row, source != "branch")
        self.package_form.setRowVisible(self.branch, source == "branch")
        self.package_form.setRowVisible(self.wheelhouse_row, source == "offline")
        self.source_hint.setText(
            {
                "release": "Latest checks PyPI again when you install.",
                "branch": "Uses the selected branch, tag or commit from the official repository. Git is required.",
                "offline": "Latest uses the newest stable MCP wheel in this folder or ZIP. No network is used.",
            }[source]
        )
        self.server_options.setEnabled(not busy)
        self.http_port.setEnabled(not server.active)
        self.solver_section.setEnabled(not server.active)
        self.server_advanced_toggle.setEnabled(not server.active)
        self.server_advanced.setEnabled(not server.active)
        self.http_section.setVisible(product.http_flags is not None)
        self.stdio_notice.setVisible(product.http_flags is None)
        self.solver_section.setVisible(bool(product.connect_flag))
        self.solver_fields.setVisible(self.connect.isChecked())
        self.aedt_section.setVisible(product.key == "pyaedt")
        self.start_button.setVisible(product.http_flags is not None)
        self.stop_button.setVisible(product.http_flags is not None)
        self.start_button.setEnabled(
            installed
            and product.http_flags is not None
            and not server.active
            and not busy
        )
        self.stop_button.setEnabled(server.active)
        self.endpoint.setText(f"http://127.0.0.1:{self.http_port.value()}/mcp")
        self.server_status.setText(
            (
                server.state
                if installed or server.active
                else "Install this MCP in Installation before starting a server."
            )
            if product.http_flags
            else "Automatic connection: the coding agent starts this server."
        )
        self.write_profile_button.setEnabled(installed and not busy)
        self.write_profile_button.setToolTip(
            "Review the configuration before saving it."
            if self._profile_preview is None
            else "Save the reviewed configuration and create a backup."
        )

    def _browse_python(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select a Python executable"
        )
        if filename:
            self.select_python(filename)

    def _browse_environment(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select an existing virtual or conda environment"
        )
        if directory:
            self.select_environment(directory)

    def _browse_wheelhouse(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select wheelhouse ZIP (or cancel to choose a directory)",
            filter="Wheelhouse (*.zip)",
        )
        if not filename:
            filename = QtWidgets.QFileDialog.getExistingDirectory(
                self, "Select wheel directory"
            )
        if filename:
            self.wheelhouse_path.setText(filename)

    def _background(self, function, complete):
        task = _Task(function)
        self._tasks.append(task)
        task.signals.completed.connect(complete)
        task.signals.finished.connect(self._task_finished)
        QtCore.QThreadPool.globalInstance().start(task)

    @QtCore.Slot(object)
    def _task_finished(self, task):
        if task in self._tasks:
            self._tasks.remove(task)

    def _fetch_versions(self):
        if self._closed or self.source.currentData() != "release":
            return
        product = self.product
        cached = self._versions.get(product.key)
        if cached:
            self._set_versions(cached[1])
            if time.monotonic() - cached[0] < 900:
                return
        if product.key in self._version_pending:
            return
        self._version_pending.add(product.key)
        self.version.setToolTip("Loading releases… Latest is always available.")

        def fetch():
            try:
                return product.key, available_versions(product), None
            except Exception as error:
                return product.key, [], str(error)

        self._background(fetch, self._versions_fetched)

    def _set_versions(self, versions):
        selected = self._version()
        with QtCore.QSignalBlocker(self.version):
            self.version.clear()
            self.version.addItem("Latest", "")
            self.version.addItems(versions)
            if selected:
                self.version.setCurrentText(selected)

    @QtCore.Slot(object, object)
    def _versions_fetched(self, result, error):
        if self._closed:
            return
        # Each request carries its product key; product switches cannot mislabel releases.
        key, versions, error = result
        self._version_pending.discard(key)
        if error:
            if self.product.key == key:
                self.version.setToolTip(
                    "Releases could not be loaded. Use Latest or enter a version; opening this list retries."
                )
            return
        self._versions[key] = (time.monotonic(), versions)
        if self.product.key == key and self.source.currentData() == "release":
            self._set_versions(versions)
            self.version.setToolTip("Latest is resolved again on every installation.")

    def _install(self, upgrade, validate_only=False):
        if self.queue.active or self._preparing:
            raise ValueError("Wait for the current installation to finish.")
        if self.environment_in_use(self.environment):
            raise ValueError("Stop the server before modifying its environment.")
        offline = self.source.currentData() == "offline"
        source = "release" if offline else self.source.currentData()
        version = self._version()
        branch = self.branch.text().strip()
        package_requirement(self.product, source, version, branch)
        self._save(announce=False)
        self._install_product = self.product
        self._install_root = self.environment
        self._install_custom = self._custom_environment()
        self._validate_only = validate_only
        options = dict(
            version=version,
            source=source,
            branch=branch,
            custom=self._install_custom,
            upgrade=upgrade,
        )
        if offline:
            source_path = self.wheelhouse_path.text().strip()
            if not source_path:
                raise ValueError("Choose an offline wheelhouse directory or ZIP.")
            self._wheelhouse = tempfile.TemporaryDirectory(prefix="pyansys-mcp-wheels-")
            options.update(
                wheelhouse=source_path, extract_to=Path(self._wheelhouse.name)
            )
        product, root, base = (
            self.product,
            self._install_root,
            self._base_python(),
        )
        self._compatibility_timer.stop()
        self._compatibility_revision += 1
        self._compatibility_pending = False
        self._preparing = True
        self._prepare_cancelled = False
        self.status.setText("Checking the selected release and supported Python…")
        self._refresh()
        self._background(
            lambda: prepare_installation(product, root, base, **options),
            self._installation_prepared,
        )

    @QtCore.Slot(object, object)
    def _installation_prepared(self, plan, error):
        self._preparing = False
        if self._closed or self._prepare_cancelled:
            self._cleanup_wheelhouse()
            if not self._closed:
                self.status.setText("Preparation cancelled.")
                self._refresh()
            return
        if error:
            self._error(error)
            self._cleanup_wheelhouse()
            self._refresh()
            return
        self._try(lambda: self._begin_install(plan))

    def _begin_install(self, plan):
        try:
            self._install_release = plan.release
            if plan.creating_environment and not self._install_custom:
                with QtCore.QSignalBlocker(self.python_select):
                    self._select_path(self.python_select, plan.interpreter.executable)
            details = (
                f"Selected {self.product.name} {plan.release.version}; release requires Python "
                f"{plan.release.requires_python}; using Python {plan.interpreter.version} (64-bit)."
            )
            self.python_hint.setText(details)
            self._append_log(self.product.key, details + "\n")
            self._save(announce=False)
            if self._validate_only:
                self.status.setText(details)
                self._cleanup_wheelhouse()
                return
            # Ensure the parent exists; venv itself creates the environment only
            # after the interpreter preflight succeeds.
            self._install_root.parent.mkdir(parents=True, exist_ok=True)
            self.status.setText(
                f"Installing {self.product.name} {plan.release.version}…"
            )
            self.queue.start(plan.commands)
        except Exception:
            self._cleanup_wheelhouse()
            raise
        finally:
            self._refresh()

    @QtCore.Slot(bool, str)
    def _installed(self, success, message):
        self._cleanup_wheelhouse()
        if (
            success
            and not console_executable(
                self._install_root, self._install_product
            ).is_file()
        ):
            success = False
            message = "Package command was not found after installation. See the log."
        if success and not self._install_release.version.startswith("Git:"):
            actual = installed_version(self._install_root, self._install_product)
            if actual != self._install_release.version:
                success = False
                message = f"Expected {self._install_release.version}, but found {actual}. Installation was not verified."
            else:
                message = f"Installation completed: {self._install_product.name} {actual}; dependencies checked."
        self.status.setText(message)
        if not success:
            self._error(message)
        self._refresh()
        parent = self._manager
        if success and parent is not None and hasattr(parent, "installed_table_tab"):
            parent.installed_table_tab.update_table()
        if success:
            self._refresh_choices()

    def _cleanup_wheelhouse(self):
        if self._wheelhouse is not None:
            self._wheelhouse.cleanup()
            self._wheelhouse = None

    def _cancel_install(self):
        if self._preparing:
            self._prepare_cancelled = True
            self.status.setText("Cancelling installation preflight…")
            # The background extractor owns this directory until its callback.
            self._refresh()
        self.queue.cancel()

    def _arguments(self, transport):
        extra = json.loads(self.extra.toPlainText())
        if not isinstance(extra, list) or any(
            not isinstance(value, str) or "\0" in value for value in extra
        ):
            raise ValueError(
                "Extra arguments must be a JSON array of strings without null characters."
            )
        product = self.product
        if self._launch_values and self._launch_context != self._launch_signature():
            self._load_launch_options()
            raise ValueError(
                "Launch options are being checked for this installation. Please try again when they finish loading."
            )
        arguments = option_arguments(self._launch_schema, self._launch_values)
        if product.connect_flag and self.connect.isChecked():
            arguments.extend(
                [
                    product.connect_flag,
                    product.machine_flag,
                    self.machine.text().strip() or "127.0.0.1",
                    "--port",
                    str(self.solver_port.value()),
                ]
            )
        if product.key == "pyaedt":
            for field, flag in (
                (self.graphical, "--graphical"),
                (self.context, "--include-context"),
                (self.dynamic, "--dynamic-tool-discovery"),
            ):
                if field.isChecked():
                    arguments.append(flag)
        return server_arguments(
            product, transport, self.http_port.value(), [*arguments, *extra]
        )

    def _launch_signature(self):
        try:
            return (
                self.product.key,
                str(self.environment),
                installed_version(self.environment, self.product),
            )
        except (ValueError, OSError):
            return None

    def _load_launch_options(self):
        signature = self._launch_signature()
        if not signature or not signature[2]:
            self.launch_hint.setText(
                "Install this MCP to see its supported launch options."
            )
            return
        if signature == self._launch_context or signature in self._launch_pending:
            return
        self._launch_context = None
        self._launch_schema = []
        self.launch_choice.setEnabled(False)
        self.launch_hint.setText("Reading options from the installed MCP…")
        self._launch_pending.add(signature)
        product, root = self.product, self.environment

        def inspect():
            try:
                return signature, launch_options(root, product), None
            except Exception as error:
                return signature, [], str(error)

        self._background(inspect, self._launch_loaded)

    @QtCore.Slot(object, object)
    def _launch_loaded(self, result, error):
        if self._closed:
            return
        signature, schema, error = result
        self._launch_pending.discard(signature)
        if signature != self._launch_signature():
            return
        if error:
            self.launch_hint.setText(
                f"{error} Custom arguments remain available below."
            )
            return
        self._launch_context = signature
        # These options already have dedicated, validated controls in APM.
        managed = {
            "--transport",
            "--http-host",
            "--http-port",
            "--host",
            "--connect",
            "--connect-on-startup",
            "--machine",
            "--ip",
            "--port",
            "--graphical",
            "--non-graphical",
            "--include-context",
            "--dynamic-tool-discovery",
        }
        self._launch_schema = [
            option for option in schema if not managed.intersection(option["flags"])
        ]
        self.launch_hint.setText(
            f"Options for installed release {signature[2]}. Transport and connection settings are managed above."
            if schema
            else "This MCP has no command-line launch options. Environment variables can be set below."
        )
        self._render_launch_options()

    def _render_launch_options(self):
        while self.launch_rows.count():
            item = self.launch_rows.takeAt(0)
            item.widget().deleteLater()
        with QtCore.QSignalBlocker(self.launch_choice):
            self.launch_choice.clear()
            self.launch_choice.addItem("Add an option…", None)
            for option in self._launch_schema:
                flag = option["flags"][0]
                if flag not in self._launch_values:
                    self.launch_choice.addItem(
                        flag.removeprefix("--").replace("-", " ").capitalize(), flag
                    )
                    self.launch_choice.setItemData(
                        self.launch_choice.count() - 1,
                        option["help"],
                        QtCore.Qt.ToolTipRole,
                    )
        self.launch_choice.setEnabled(bool(self._launch_schema))
        schema = {option["flags"][0]: option for option in self._launch_schema}
        for flag, value in self._launch_values.items():
            row = QtWidgets.QWidget()
            layout = QtWidgets.QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            label = self._label(flag)
            layout.addWidget(label)
            option = schema.get(flag)
            if not option:
                layout.addWidget(self._label("Awaiting validation for this release"), 1)
            elif option["kind"] == "flag":
                layout.addWidget(self._label("Enabled"), 1)
            else:
                if option["choices"]:
                    editor = self._compact_combo(QtWidgets.QComboBox())
                    editor.addItems([str(choice) for choice in option["choices"]])
                    editor.setCurrentText(str(value))
                    editor.currentTextChanged.connect(
                        lambda text, flag=flag: self._set_launch_value(flag, text)
                    )
                else:
                    editor = QtWidgets.QLineEdit(
                        json.dumps(value) if isinstance(value, list) else str(value)
                    )
                    editor.setPlaceholderText(
                        'JSON array, e.g. ["value"]'
                        if option["nargs"] in ("+", "*")
                        or (type(option["nargs"]) is int and option["nargs"] > 0)
                        else "Value"
                    )
                    editor.textChanged.connect(
                        lambda text, flag=flag, option=option: self._edit_launch_value(
                            flag, text, option
                        )
                    )
                editor.setAccessibleName(flag)
                editor.setToolTip(option["help"] + f"\nDefault: {option['default']}")
                layout.addWidget(editor, 1)
            layout.addWidget(
                self._button(
                    "Remove", lambda flag=flag: self._remove_launch_option(flag)
                )
            )
            self.launch_rows.addWidget(row)

    def _add_launch_option(self, index):
        flag = self.launch_choice.itemData(index)
        if not flag:
            return
        option = next(
            option for option in self._launch_schema if option["flags"][0] == flag
        )
        self._launch_values[flag] = (
            True if option["kind"] == "flag" else str(option["default"] or "")
        )
        if option["nargs"] in ("+", "*") or (
            type(option["nargs"]) is int and option["nargs"] > 0
        ):
            self._launch_values[flag] = []
        self._render_launch_options()
        self._launch_options_changed()

    def _set_launch_value(self, flag, value):
        self._launch_values[flag] = value
        self._launch_options_changed()

    def _edit_launch_value(self, flag, text, option):
        value = text
        if option["nargs"] in ("+", "*") or (
            type(option["nargs"]) is int and option["nargs"] > 0
        ):
            try:
                value = json.loads(text)
            except ValueError:
                value = None
        self._set_launch_value(flag, value)

    def _remove_launch_option(self, flag):
        self._launch_values.pop(flag, None)
        self._render_launch_options()
        self._launch_options_changed()

    def _environment_variables(self):
        values = json.loads(self.environment_json.toPlainText())
        if not isinstance(values, dict) or any(
            not isinstance(key, str)
            or not key
            or "=" in key
            or "\0" in key
            or not isinstance(value, str)
            or "\0" in value
            for key, value in values.items()
        ):
            raise ValueError(
                "Environment variables must be a JSON object of string names and values."
            )
        return values

    def _start_server(self):
        arguments = self._arguments("http")
        environment = self._environment_variables()
        root = self.environment
        executable = console_executable(root, self.product)
        if not executable.is_file():
            raise ValueError("Install this MCP before starting its server.")
        self._save(announce=False)
        self.servers[self.product.key].environment_root = root
        self.servers[self.product.key].start(
            executable, arguments, self.http_port.value(), environment
        )
        self._refresh()

    def environment_in_use(self, directory):
        """Protect an environment from deletion or mutation while the manager uses it."""
        root = Path(directory).resolve()
        if (self.queue.active or self._preparing) and hasattr(self, "_install_root"):
            if self._install_root.resolve() == root:
                return True
        return any(
            server.active
            and getattr(server, "environment_root", None) is not None
            and server.environment_root.resolve() == root
            for server in self.servers.values()
        )

    def _server_changed(self, key):
        if key == self.product.key:
            self._refresh()

    def _transport(self):
        return self.transport.currentData() or "stdio"

    def _update_transports(self, preferred=None):
        selected = preferred or self._transport()
        with QtCore.QSignalBlocker(self.transport):
            self.transport.clear()
            self.transport.addItem("Automatic (stdio)", "stdio")
            if (
                self.product.http_flags
                and self.client.currentText() != "Claude Desktop"
            ):
                self.transport.addItem("Shared HTTP server", "http")
            index = self.transport.findData(selected)
            self.transport.setCurrentIndex(index if index >= 0 else 0)
        self._connection_changed()

    def _client_changed(self):
        client = self.client.currentText()
        self.vscode_format.setVisible(client == "VS Code")
        self.workspace_button.setVisible(client == "VS Code")
        self._vscode_format_changed()
        self._update_transports()

    def _vscode_format_changed(self, *_):
        if self.client.currentText() == "VS Code" and self.vscode_format.currentData():
            config = (
                Path(os.environ.get("APPDATA") or Path.home() / "AppData/Roaming")
                if os.name == "nt"
                else Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
            )
            path = config / "Code/User/mcp.json"
        else:
            path = default_profile_path(self.client.currentText())
        self.profile_path.setText(str(path))
        self._connection_changed()

    def _connection_changed(self, *_):
        self.client_hint.setText(
            f"Start the HTTP server in Server settings before using this agent. APM must stay open."
            if self._transport() == "http"
            else "Your coding agent starts this MCP automatically. APM can be closed afterward."
        )
        self.profile_hint.setText(
            "Personal configuration selected. Choose a workspace for a project configuration. Current Copilot uses mcpServers; the legacy Local harness uses servers. Existing settings are preserved and backed up."
            if self.client.currentText() == "VS Code"
            else "Existing settings are preserved. A backup is saved before updating the file."
        )
        self._invalidate_preview()

    def _launch_options_changed(self, *_):
        configured = (
            bool(self._launch_values)
            or any(
                field.isChecked()
                for field in (self.graphical, self.context, self.dynamic)
            )
            or self.extra.toPlainText().strip() not in ("", "[]")
            or self.environment_json.toPlainText().strip() not in ("", "{}")
        )
        self.server_advanced_toggle.setText(
            "Advanced launch settings · customized"
            if configured
            else "Advanced launch settings"
        )
        self._invalidate_preview()

    def _browse_workspace(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select a VS Code workspace folder"
        )
        if directory:
            relative = (
                ".vscode/mcp.json" if self.vscode_format.currentData() else ".mcp.json"
            )
            self.profile_path.setText(str(Path(directory) / relative))

    def _browse_profile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose the coding agent configuration file", self.profile_path.text()
        )
        if filename:
            self.profile_path.setText(filename)

    def _invalidate_preview(self, *_):
        self._profile_preview = None
        self.preview.clear()
        self.preview_section.hide()
        self.write_profile_button.setText("Review configuration…")
        if (
            hasattr(self, "status")
            and self.status.text() == "Review the changes, then save the configuration."
        ):
            self.status.clear()

    def _preview_profile(self):
        if self.queue.active or self._preparing:
            raise ValueError(
                "Wait for installation to finish before configuring a client."
            )
        executable = console_executable(self.environment, self.product)
        if not executable.is_file():
            raise ValueError("Install this MCP before configuring a client.")
        if not self.profile_path.text().strip():
            raise ValueError("Choose a client configuration file.")
        path = Path(self.profile_path.text()).expanduser().absolute()
        original = path.read_text(encoding="utf-8") if path.exists() else ""
        transport = self._transport()
        arguments = self._arguments("stdio")
        rendered = render_profile(
            self.client.currentText(),
            original,
            self.product,
            executable,
            arguments,
            transport=transport,
            port=self.http_port.value(),
            vscode_legacy=bool(self.vscode_format.currentData()),
        )
        # Profiles retain environment overrides for client-owned stdio processes.
        environment = self._environment_variables()
        if environment and transport == "stdio":
            if self.client.currentText() == "Codex":
                import tomlkit

                data = tomlkit.parse(rendered)
                data["mcp_servers"][f"{self.product.key}-mcp"]["env"] = environment
                rendered = tomlkit.dumps(data)
            else:
                data = json.loads(rendered)
                client = self.client.currentText()
                container = (
                    "servers"
                    if client == "VS Code" and self.vscode_format.currentData()
                    else "mcp" if client == "OpenCode" else "mcpServers"
                )
                field = "environment" if client == "OpenCode" else "env"
                data[container][f"{self.product.key}-mcp"][field] = environment
                rendered = json.dumps(data, indent=2) + "\n"
        self.preview.setPlainText(rendered)
        self.preview_section.show()
        self._profile_preview = (path, original, rendered)
        self.write_profile_button.setEnabled(True)
        self.write_profile_button.setText("Save reviewed configuration")
        self.status.setText("Review the changes, then save the configuration.")

    def _review_or_write_profile(self):
        if self._profile_preview is None:
            self._preview_profile()
        else:
            self._write_profile()

    def _write_profile(self):
        if self._profile_preview is None:
            raise ValueError("Preview the profile before installing it.")
        path, original, rendered = self._profile_preview
        backup = save_profile(path, original, rendered)
        self.status.setText(
            f"Profile saved to {path}. Reload the client."
            + (f" Backup: {backup}" if backup else "")
        )
        self._profile_preview = None
        self.write_profile_button.setText("Review configuration…")

    def shutdown(self, save_settings=True):
        """Stop owned processes and persist the selected product's settings."""
        if self._closed:
            return
        self._closed = True
        self._compatibility_timer.stop()
        self._compatibility_revision += 1
        if save_settings:
            self._try(lambda: self._save(announce=False))
        self.queue.shutdown()
        for server in self.servers.values():
            server.shutdown()
        if not self._preparing:
            self._cleanup_wheelhouse()

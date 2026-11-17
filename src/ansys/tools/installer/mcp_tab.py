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

from html import escape
import json
from pathlib import Path
import sys
import tempfile

from PySide6 import QtCore, QtGui, QtWidgets

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
from ansys.tools.installer.mcp_process import CommandQueue, McpServer
from ansys.tools.installer.mcp_profiles import (
    CLIENTS,
    default_profile_path,
    render_profile,
    save_profile,
)


class _Signals(QtCore.QObject):
    completed = QtCore.Signal(object, object)


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
        self._wheelhouse = None
        self._profile_preview = None
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
        if self.custom_environment.isChecked():
            value = self.environment_path.text().strip()
            if not value:
                raise ValueError("Choose an existing environment folder.")
            return Path(value).expanduser().absolute()
        return self.directory / "environments" / self.product.key

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

    def _build(self):
        layout = QtWidgets.QVBoxLayout(self)
        self.product_select = QtWidgets.QComboBox()
        self.product_select.setAccessibleName("PyAnsys MCP product")
        self.product_select.addItems([product.name for product in PRODUCTS])
        layout.addWidget(self.product_select)
        self.description = QtWidgets.QLabel()
        self.description.setWordWrap(True)
        self.description.setOpenExternalLinks(True)
        layout.addWidget(self.description)
        self.installed_label = QtWidgets.QLabel()
        self.installed_label.setWordWrap(True)
        layout.addWidget(self.installed_label)
        self.pages = QtWidgets.QTabWidget()
        layout.addWidget(self.pages, 1)
        self._setup_page()
        self._server_page()
        self._client_page()
        layout.addWidget(self.install_actions)
        layout.addWidget(self.server_actions)
        self.server_actions.setVisible(False)
        self.pages.currentChanged.connect(
            lambda index: self.install_actions.setVisible(index == 0)
        )
        self.pages.currentChanged.connect(
            lambda index: self.server_actions.setVisible(index == 1)
        )
        self.status = QtWidgets.QLabel("Ready to set up an MCP.")
        self.status.setWordWrap(True)
        self.status.setTextFormat(QtCore.Qt.PlainText)
        self.status.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.status)
        self.log_group = QtWidgets.QGroupBox("Installation and server log")
        self.log_group.setCheckable(True)
        self.log_group.setChecked(False)
        log_layout = QtWidgets.QVBoxLayout(self.log_group)
        self.log = QtWidgets.QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setMaximumHeight(170)
        self.log.setVisible(False)
        log_layout.addWidget(self.log)
        self.log_group.toggled.connect(self.log.setVisible)
        layout.addWidget(self.log_group)

    def _setup_page(self):
        layout = self._page(self.pages, "Installation")
        help_text = QtWidgets.QLabel(
            "Install each MCP in its own environment. Install a compatible 64-bit Python "
            "in the Install Python tab first. Solver installations and licenses are separate."
        )
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        self.install_options = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self.install_options)
        self.base_python = QtWidgets.QLineEdit(
            "" if getattr(sys, "frozen", False) else sys.executable
        )
        self.base_python.setPlaceholderText(
            "Path to a compatible python.exe or python3"
        )
        form.addRow(
            "Base Python",
            self._field_with_browse(self.base_python, self._browse_python),
        )
        form.addRow(
            self._button(
                "Use Python selected in Create environments", self._use_selected_python
            )
        )
        form.addRow(
            self._button(
                "Find supported Python",
                lambda: self._install(False, validate_only=True),
            )
        )
        self.python_hint = QtWidgets.QLabel()
        self.python_hint.setWordWrap(True)
        self.python_hint.setTextFormat(QtCore.Qt.PlainText)
        form.addRow(self.python_hint)
        self.custom_environment = QtWidgets.QCheckBox(
            "Use an existing virtual or conda environment"
        )
        form.addRow(self.custom_environment)
        self.environment_path = QtWidgets.QLineEdit()
        self.environment_row = self._field_with_browse(
            self.environment_path, self._browse_environment
        )
        form.addRow("Environment", self.environment_row)
        form.addRow(
            self._button(
                "Use environment selected in Manage environments",
                self._use_selected_environment,
            )
        )
        self.environment_hint = QtWidgets.QLabel()
        self.environment_hint.setWordWrap(True)
        self.environment_hint.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        form.addRow(self.environment_hint)
        self.source = QtWidgets.QComboBox()
        self.source.addItem("PyPI release", "release")
        self.source.addItem("Official Git repository (requires Git)", "branch")
        form.addRow("Install from", self.source)
        self.version = QtWidgets.QComboBox()
        self.version.setEditable(True)
        self.version.addItem("Latest", "")
        self.version.setToolTip(
            "Latest checks PyPI on every installation and installs that exact release."
        )
        version_row = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(version_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.version, 1)
        self.versions_button = self._button("Fetch versions", self._fetch_versions)
        row.addWidget(self.versions_button)
        form.addRow("Release version", version_row)
        self.branch = QtWidgets.QLineEdit("main")
        form.addRow("Git branch / tag", self.branch)
        self.offline = QtWidgets.QCheckBox(
            "Offline: install only from a local wheelhouse"
        )
        form.addRow(self.offline)
        self.wheelhouse_path = QtWidgets.QLineEdit()
        self.wheelhouse_path.setPlaceholderText("Wheel directory or wheelhouse ZIP")
        form.addRow(
            "Wheelhouse",
            self._field_with_browse(self.wheelhouse_path, self._browse_wheelhouse),
        )
        layout.addWidget(self.install_options)
        self.install_actions = QtWidgets.QWidget()
        buttons = QtWidgets.QHBoxLayout(self.install_actions)
        buttons.setContentsMargins(0, 0, 0, 0)
        self.install_button = self._button("Install", lambda: self._install(False))
        self.update_button = self._button(
            "Update / repair", lambda: self._install(True)
        )
        self.cancel_button = self._button("Cancel", self._cancel_install)
        self.save_button = self._button("Save settings", self._save)
        for button in (
            self.install_button,
            self.update_button,
            self.cancel_button,
            self.save_button,
        ):
            buttons.addWidget(button)
        layout.addStretch()
        self.custom_environment.toggled.connect(self._options_changed)
        self.environment_path.textChanged.connect(self._options_changed)
        self.source.currentIndexChanged.connect(self._options_changed)
        self.offline.toggled.connect(self._options_changed)

    def _server_page(self):
        layout = self._page(self.pages, "Server settings")
        text = QtWidgets.QLabel(
            "Stdio clients start their own MCP process. For HTTP, start a shared server here; "
            "it listens on this computer only. Closing the manager stops servers it started."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        self.server_options = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(self.server_options)
        self.http_port = QtWidgets.QSpinBox()
        self.http_port.setRange(1, 65535)
        form.addRow("HTTP port", self.http_port)
        self.connect = QtWidgets.QCheckBox("Connect to a running solver on startup")
        form.addRow(self.connect)
        self.machine = QtWidgets.QLineEdit("127.0.0.1")
        form.addRow("Solver host", self.machine)
        self.solver_port = QtWidgets.QSpinBox()
        self.solver_port.setRange(1, 65535)
        form.addRow("Solver port", self.solver_port)
        self.graphical = QtWidgets.QCheckBox("Graphical AEDT")
        self.context = QtWidgets.QCheckBox("Include AEDT context tools")
        self.dynamic = QtWidgets.QCheckBox("Dynamic AEDT tool discovery")
        for field in (self.graphical, self.context, self.dynamic):
            form.addRow(field)
        self.extra = QtWidgets.QPlainTextEdit("[]")
        self.extra.setMaximumHeight(80)
        self.extra.setPlaceholderText(
            '["--transport-mode", "mtls", "--certs-dir", "C:/certs"]'
        )
        form.addRow("Extra CLI arguments\n(JSON string array)", self.extra)
        self.extra.setToolTip(
            "Use the selected MCP's documented CLI options. Paths are individual array values."
        )
        self.environment_json = QtWidgets.QPlainTextEdit("{}")
        self.environment_json.setMaximumHeight(80)
        self.environment_json.setToolTip(
            "Passed to HTTP servers and stdio client profiles. Values are stored as plain text."
        )
        form.addRow("Environment variables\n(JSON object)", self.environment_json)
        layout.addWidget(self.server_options)
        self.server_actions = QtWidgets.QWidget()
        actions = QtWidgets.QVBoxLayout(self.server_actions)
        actions.setContentsMargins(0, 0, 0, 0)
        buttons = QtWidgets.QHBoxLayout()
        self.start_button = self._button("Start HTTP server", self._start_server)
        self.stop_button = self._button(
            "Stop server", lambda: self.servers[self.product.key].stop()
        )
        self.refresh_button = self._button("Refresh status", self._refresh)
        for button in (self.start_button, self.stop_button, self.refresh_button):
            buttons.addWidget(button)
        actions.addLayout(buttons)
        self.server_status = QtWidgets.QLabel()
        self.server_status.setWordWrap(True)
        self.server_status.setTextFormat(QtCore.Qt.PlainText)
        actions.addWidget(self.server_status)
        layout.addStretch()

    def _client_page(self):
        layout = self._page(self.pages, "Coding agents")
        text = QtWidgets.QLabel(
            "Choose a client configuration file, preview the merged document, then install. "
            "Other MCP entries are preserved and existing files are backed up. For VS Code, "
            "choose your workspace's .vscode/mcp.json. Restart or reload the client afterward."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        form = QtWidgets.QFormLayout()
        self.client = QtWidgets.QComboBox()
        self.client.addItems(CLIENTS)
        form.addRow("Coding agent", self.client)
        self.transport = QtWidgets.QComboBox()
        form.addRow("Transport", self.transport)
        self.profile_path = QtWidgets.QLineEdit()
        form.addRow(
            "Configuration file",
            self._field_with_browse(self.profile_path, self._browse_profile),
        )
        layout.addLayout(form)
        self.preview = QtWidgets.QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setPlaceholderText(
            "The merged client configuration will appear here."
        )
        layout.addWidget(self.preview, 1)
        buttons = QtWidgets.QHBoxLayout()
        buttons.addWidget(self._button("Preview profile", self._preview_profile))
        self.write_profile_button = self._button(
            "Install previewed profile", self._write_profile
        )
        buttons.addWidget(self.write_profile_button)
        layout.addLayout(buttons)
        self.client.currentTextChanged.connect(self._client_changed)
        self.transport.currentTextChanged.connect(self._invalidate_preview)
        self.profile_path.textChanged.connect(self._invalidate_preview)
        self.http_port.valueChanged.connect(self._invalidate_preview)
        self.extra.textChanged.connect(self._invalidate_preview)
        self.environment_json.textChanged.connect(self._invalidate_preview)
        for field in (self.connect, self.graphical, self.context, self.dynamic):
            field.toggled.connect(self._invalidate_preview)
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
        self.description.setText(
            f"{escape(product.description)}<br>64-bit Python {escape(product.python)}. "
            f'<a href="{product.documentation}">Official setup guide</a> · '
            f'<a href="{product.repository}">Source</a>'
        )
        self.python_hint.setText(
            "The selected release's Python requirements are checked before installation."
        )
        self.base_python.setText(
            str(values.get("base_python", self.base_python.text()))
        )
        self.custom_environment.setChecked(values.get("custom", False) is True)
        self.environment_path.setText(str(values.get("environment", "")))
        self.source.setCurrentIndex(1 if values.get("source") == "branch" else 0)
        self.version.clear()
        self.version.addItem("Latest", "")
        version = str(values.get("version", ""))
        if version:
            self.version.addItem(version, version)
            self.version.setCurrentIndex(1)
        self.branch.setText(str(values.get("branch", "main")))
        self.offline.setChecked(values.get("offline", False) is True)
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
        self.environment_json.setPlainText(str(values.get("env", "{}")))
        self.transport.clear()
        self.transport.addItem("stdio")
        if product.http_flags:
            self.transport.addItem("http")
        self.log.setPlainText(self._logs[product.key])
        self._loading = False
        self._invalidate_preview()
        self._refresh()

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
            "base_python": self.base_python.text().strip(),
            "custom": self.custom_environment.isChecked(),
            "environment": self.environment_path.text().strip(),
            "source": self.source.currentData(),
            "version": self._version(),
            "branch": self.branch.text().strip(),
            "offline": self.offline.isChecked(),
            "wheelhouse": self.wheelhouse_path.text().strip(),
            "http_port": self.http_port.value(),
            "solver_port": self.solver_port.value(),
            "connect": self.connect.isChecked(),
            "machine": self.machine.text().strip(),
            "graphical": self.graphical.isChecked(),
            "context": self.context.isChecked(),
            "dynamic": self.dynamic.isChecked(),
            "extra": self.extra.toPlainText(),
            "env": self.environment_json.toPlainText(),
        }
        atomic_write(self.settings_path, json.dumps(self.settings, indent=2) + "\n")
        if announce:
            self.status.setText("MCP settings saved.")

    def _options_changed(self):
        if self._loading:
            return
        self._invalidate_preview()
        self._refresh()

    def _refresh(self):
        product = self.product
        server = self.servers[product.key]
        busy = self.queue.active or self._preparing
        environment_busy = False
        try:
            root = self.environment
            environment_busy = self.environment_in_use(root)
            version = installed_version(root, product)
            installed = console_executable(root, product).is_file() and bool(version)
            self.installed_label.setText(
                f"Installed: {version}"
                if installed
                else "MCP is not installed in this environment."
            )
            self.environment_hint.setText(f"Environment: {root}")
        except (ValueError, OSError) as error:
            installed = False
            self.installed_label.setText(str(error))
        self.product_select.setEnabled(not busy)
        self.install_options.setEnabled(not busy and not server.active)
        self.install_button.setEnabled(not busy and not environment_busy)
        self.update_button.setEnabled(not busy and not environment_busy)
        self.cancel_button.setEnabled(busy)
        self.save_button.setEnabled(not busy)
        self.environment_row.setEnabled(self.custom_environment.isChecked())
        self.base_python.setEnabled(not self.custom_environment.isChecked())
        self.branch.setEnabled(
            self.source.currentData() == "branch" and not self.offline.isChecked()
        )
        self.source.setEnabled(not self.offline.isChecked())
        self.version.setEnabled(self.source.currentData() == "release")
        self.wheelhouse_path.setEnabled(self.offline.isChecked())
        self.server_options.setEnabled(not server.active and not busy)
        self.http_port.setEnabled(product.http_flags is not None)
        for field in (self.connect, self.machine, self.solver_port):
            field.setVisible(bool(product.connect_flag))
        form = self.server_options.layout()
        for field in (self.machine, self.solver_port):
            form.labelForField(field).setVisible(bool(product.connect_flag))
        for field in (self.graphical, self.context, self.dynamic):
            field.setVisible(product.key == "pyaedt")
        self.start_button.setEnabled(
            installed
            and product.http_flags is not None
            and not server.active
            and not busy
        )
        self.stop_button.setEnabled(server.active)
        self.server_status.setText(
            server.state
            if product.http_flags
            else "Stdio only: the coding agent starts this server."
        )
        self.write_profile_button.setEnabled(
            self._profile_preview is not None and not busy
        )

    def _browse_python(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Select a compatible Python executable"
        )
        if filename:
            self.base_python.setText(filename)

    def _use_selected_python(self):
        parent = self._manager
        if parent is None or not hasattr(parent, "venv_table_tab"):
            raise ValueError("Select a Python executable with Browse.")
        path = parent.venv_table_tab.table.active_path
        if not path or path == "None":
            raise ValueError(
                "Select a Python installation in Create environments first."
            )
        self.base_python.setText(str(python_executable(path)))

    def _use_selected_environment(self):
        parent = self._manager
        if parent is None or not hasattr(parent, "installed_table_tab"):
            raise ValueError("Select an existing environment with Browse.")
        path = parent.installed_table_tab.venv_table.active_path
        if not path or path == "None":
            raise ValueError("Select an environment in Manage environments first.")
        root = Path(path)
        if root.name in ("Scripts", "bin"):
            root = root.parent
        self.custom_environment.setChecked(True)
        self.environment_path.setText(str(root))

    def _browse_environment(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select an existing virtual or conda environment"
        )
        if directory:
            self.environment_path.setText(directory)

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
        QtCore.QThreadPool.globalInstance().start(task)

    def _fetch_versions(self):
        product = self.product
        self.versions_button.setEnabled(False)
        self.status.setText(f"Fetching {product.name} releases…")
        self._version_product = product.key
        self._background(lambda: available_versions(product), self._versions_fetched)

    @QtCore.Slot(object, object)
    def _versions_fetched(self, versions, error):
        if self._closed:
            return
        self.versions_button.setEnabled(True)
        if self.product.key != self._version_product:
            return
        if error:
            self._error(
                f"Could not fetch versions: {error}. You can enter a version manually."
            )
            return
        selected = self._version()
        self.version.clear()
        self.version.addItem("Latest", "")
        self.version.addItems(versions)
        if selected:
            self.version.setCurrentText(selected)
        self.status.setText(
            "Release list updated. Latest always checks PyPI again before installation."
        )

    def _install(self, upgrade, validate_only=False):
        if self.queue.active or self._preparing:
            raise ValueError("Wait for the current installation to finish.")
        if self.environment_in_use(self.environment):
            raise ValueError("Stop the server before modifying its environment.")
        source = "release" if self.offline.isChecked() else self.source.currentData()
        version = self._version()
        branch = self.branch.text().strip()
        package_requirement(self.product, source, version, branch)
        self._save(announce=False)
        self._install_product = self.product
        self._install_root = self.environment
        self._install_custom = self.custom_environment.isChecked()
        self._validate_only = validate_only
        options = dict(
            version=version,
            source=source,
            branch=branch,
            custom=self._install_custom,
            upgrade=upgrade,
        )
        if self.offline.isChecked():
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
            self.base_python.text().strip(),
        )
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
                self.base_python.setText(plan.interpreter.executable)
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
            self.status.setText("Installing MCP…")
            self.log_group.setChecked(True)
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
        arguments = []
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
        self.log_group.setChecked(True)
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

    def _client_changed(self):
        self.profile_path.setText(str(default_profile_path(self.client.currentText())))
        self._invalidate_preview()

    def _browse_profile(self):
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose the coding agent configuration file", self.profile_path.text()
        )
        if filename:
            self.profile_path.setText(filename)

    def _invalidate_preview(self, *_):
        self._profile_preview = None
        self.preview.clear()
        self.write_profile_button.setEnabled(False)

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
        transport = self.transport.currentText()
        arguments = self._arguments("stdio")
        rendered = render_profile(
            self.client.currentText(),
            original,
            self.product,
            executable,
            arguments,
            transport=transport,
            port=self.http_port.value(),
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
                    if client == "VS Code"
                    else "mcp" if client == "OpenCode" else "mcpServers"
                )
                field = "environment" if client == "OpenCode" else "env"
                data[container][f"{self.product.key}-mcp"][field] = environment
                rendered = json.dumps(data, indent=2) + "\n"
        self.preview.setPlainText(rendered)
        self._profile_preview = (path, original, rendered)
        self.write_profile_button.setEnabled(True)
        self.status.setText(
            "Review the configuration below, then install the previewed profile."
        )

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
        self.write_profile_button.setEnabled(False)

    def shutdown(self, save_settings=True):
        """Stop owned processes and persist the selected product's settings."""
        if self._closed:
            return
        self._closed = True
        if save_settings:
            self._try(lambda: self._save(announce=False))
        self.queue.shutdown()
        for server in self.servers.values():
            server.shutdown()
        if not self._preparing:
            self._cleanup_wheelhouse()

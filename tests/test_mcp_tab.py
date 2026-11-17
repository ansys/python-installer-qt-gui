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

import json
import subprocess
import sys
import zipfile

import pytest

from ansys.tools.installer.mcp_backend import console_executable, installed_version
from ansys.tools.installer.mcp_catalog import PRODUCT_BY_KEY
from ansys.tools.installer.mcp_tab import McpTab


@pytest.fixture
def tab(qtbot, tmp_path):
    widget = McpTab(directory=tmp_path / "manager with spaces")
    qtbot.addWidget(widget)
    yield widget
    widget.shutdown()


def _select(tab, key):
    for index in range(tab.product_select.count()):
        if tab.product_select.itemText(index) == PRODUCT_BY_KEY[key].name:
            tab.product_select.setCurrentIndex(index)
            return
    raise AssertionError(key)


def test_product_settings_are_independent_and_persist(tab):
    tab.http_port.setValue(9090)
    tab.extra.setPlainText('["--version", "2026.1"]')
    _select(tab, "pyfluent")
    assert tab.http_port.value() != 9090
    assert tab.extra.toPlainText() == "[]"
    _select(tab, "pyaedt")
    assert tab.http_port.value() == 9090
    assert json.loads(tab.extra.toPlainText()) == ["--version", "2026.1"]
    saved = json.loads(tab.settings_path.read_text())
    assert saved["pyaedt"]["http_port"] == 9090


def test_lumerical_only_offers_stdio(tab):
    _select(tab, "pylumerical")
    assert tab.transport.count() == 1
    assert tab.transport.currentText() == "stdio"
    assert not tab.start_button.isEnabled()
    assert tab._arguments("stdio") == []


def test_aedt_connection_arguments_and_validation(tab):
    tab.connect.setChecked(True)
    tab.solver_port.setValue(50055)
    tab.graphical.setChecked(True)
    arguments = tab._arguments("http")
    assert "--connect" in arguments
    assert "--graphical" in arguments
    assert arguments[arguments.index("--port") + 1] == "50055"
    tab.extra.setPlainText('{"invalid":true}')
    with pytest.raises(ValueError, match="JSON array"):
        tab._arguments("stdio")
    tab.environment_json.setPlainText('{"BAD=NAME":"value"}')
    with pytest.raises(ValueError, match="Environment variables"):
        tab._environment_variables()


def test_corrupt_settings_are_not_silently_overwritten(qtbot, tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{corrupt")
    widget = McpTab(directory=tmp_path)
    qtbot.addWidget(widget)
    try:
        with pytest.raises(ValueError, match="Repair"):
            widget._save()
        assert path.read_text() == "{corrupt"
    finally:
        widget.shutdown()


def _wheel(directory):
    """Create a solver-free console package for an actual offline pip install."""
    name = "ansys_mechanical_mcp-0.0.0"
    files = {
        "apm_mcp_fixture.py": "def main():\n    print('fixture MCP')\n",
        f"{name}.dist-info/METADATA": "Metadata-Version: 2.1\nName: ansys-mechanical-mcp\nVersion: 0.0.0\n",
        f"{name}.dist-info/WHEEL": "Wheel-Version: 1.0\nGenerator: apm-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{name}.dist-info/entry_points.txt": "[console_scripts]\nansys-mechanical-mcp = apm_mcp_fixture:main\n",
    }
    files[f"{name}.dist-info/RECORD"] = "".join(f"{path},,\n" for path in files)
    directory.mkdir(parents=True)
    with zipfile.ZipFile(directory / f"{name}-py3-none-any.whl", "w") as archive:
        for path, content in files.items():
            archive.writestr(path, content)


@pytest.mark.skipif(
    sys.version_info < (3, 12),
    reason="MCPs require a separate Python 3.12+ interpreter",
)
def test_offline_install_through_ui_and_profile_preview(tab, qtbot, tmp_path):
    _select(tab, "pymechanical")
    wheels = tmp_path / "wheel house"
    _wheel(wheels)
    tab.base_python.setText(sys.executable)
    tab.offline.setChecked(True)
    tab.wheelhouse_path.setText(str(wheels))
    tab.version.setCurrentText("0.0.0")
    tab._install(False)
    qtbot.waitUntil(lambda: not tab._preparing and not tab.queue.active, timeout=90000)
    assert console_executable(
        tab.environment, tab.product
    ).is_file(), tab.log.toPlainText()
    assert installed_version(tab.environment, tab.product) == "0.0.0"
    assert "completed" in tab.status.text(), tab.log.toPlainText()
    tab.client.setCurrentText("Cursor")
    configuration = tmp_path / "client/mcp.json"
    configuration.parent.mkdir()
    configuration.write_text('{"mcpServers":{"existing":{"command":"keep"}}}')
    tab.profile_path.setText(str(configuration))
    tab.environment_json.setPlainText('{"EXAMPLE":"value"}')
    tab._preview_profile()
    assert "pymechanical-mcp" not in configuration.read_text()
    assert tab.write_profile_button.isEnabled()
    tab._write_profile()
    data = json.loads(configuration.read_text())["mcpServers"]
    assert data["existing"]["command"] == "keep"
    assert data["pymechanical-mcp"]["env"] == {"EXAMPLE": "value"}
    assert list(configuration.parent.glob("*.bak"))
    tab._preview_profile()
    tab.extra.setPlainText('["--static-tools"]')
    assert not tab.write_profile_button.isEnabled()


def test_invalid_install_source_shows_error_without_starting(tab):
    tab.source.setCurrentIndex(1)
    tab.branch.setText("main#bad")
    tab.install_button.click()
    assert "Git branch" in tab.status.text()
    assert not tab.queue.active


def test_shutdown_reaps_running_server(tab, qtbot):
    server = tab.servers[tab.product.key]
    server.process.start(sys.executable, ["-c", "import time; time.sleep(60)"])
    qtbot.waitUntil(lambda: server.active)
    tab.shutdown()
    assert not server.active


@pytest.mark.skipif(sys.version_info < (3, 12), reason="MCP interpreter baseline")
def test_existing_environment_without_pip_is_bootstrapped(tab, qtbot, tmp_path):
    _select(tab, "pymechanical")
    existing = tmp_path / "existing environment"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(existing)], check=True
    )
    wheels = tmp_path / "wheels"
    _wheel(wheels)
    tab.custom_environment.setChecked(True)
    tab.environment_path.setText(str(existing))
    tab.offline.setChecked(True)
    tab.wheelhouse_path.setText(str(wheels))
    tab.version.setCurrentText("0.0.0")
    tab._install(False)
    qtbot.waitUntil(lambda: not tab._preparing and not tab.queue.active, timeout=90000)
    assert "completed" in tab.status.text(), tab.log.toPlainText()
    assert installed_version(existing, tab.product) == "0.0.0"


def test_shared_custom_environment_is_protected_across_products(tab, qtbot, tmp_path):
    root = tmp_path / "shared"
    root.mkdir()
    server = tab.servers["pyaedt"]
    server.environment_root = root
    server.process.start(sys.executable, ["-c", "import time; time.sleep(60)"])
    qtbot.waitUntil(lambda: server.active)
    try:
        _select(tab, "pymechanical")
        tab.custom_environment.setChecked(True)
        tab.environment_path.setText(str(root))
        assert tab.environment_in_use(root)
        assert not tab.install_button.isEnabled()
        with pytest.raises(ValueError, match="Stop the server"):
            tab._install(False)
    finally:
        server.shutdown()


def test_each_product_renders_in_constrained_window(tab, qtbot, tmp_path):
    tab.resize(660, 620)
    tab.show()
    for index in range(tab.product_select.count()):
        tab.product_select.setCurrentIndex(index)
        for page in range(tab.pages.count()):
            tab.pages.setCurrentIndex(page)
            qtbot.wait(10)
            assert not tab.grab().isNull()
    assert tab.grab().save(str(tmp_path / "mcp-tab.png"))


def test_uninstall_can_exit_without_recreating_removed_settings(tab):
    assert not tab.settings_path.exists()
    tab.shutdown(save_settings=False)
    assert not tab.settings_path.exists()

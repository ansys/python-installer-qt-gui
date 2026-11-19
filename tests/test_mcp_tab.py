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
from pathlib import Path
import subprocess
import sys
import threading
import zipfile

from PySide6 import QtCore
import pytest

from ansys.tools.installer import installed_table, mcp_backend
from ansys.tools.installer.mcp_backend import console_executable, installed_version
from ansys.tools.installer.mcp_catalog import PRODUCT_BY_KEY
from ansys.tools.installer.mcp_releases import ReleaseInfo
from ansys.tools.installer.mcp_tab import McpTab, _Task


@pytest.fixture(autouse=True)
def discovered_environments(monkeypatch):
    """Keep UI discovery deterministic and release checks off the network."""
    monkeypatch.setattr(
        installed_table,
        "find_all_python",
        lambda: {
            str(Path(sys.executable).parent): (
                ".".join(map(str, sys.version_info[:3])),
                False,
            )
        },
    )
    monkeypatch.setattr(installed_table, "find_miniforge", lambda: {})
    monkeypatch.setattr(installed_table, "get_all_python_venv", lambda: {})
    monkeypatch.setattr(
        "ansys.tools.installer.mcp_tab.available_versions", lambda product: ["1.0"]
    )
    monkeypatch.setattr(
        mcp_backend,
        "published_release",
        lambda product, version="": ReleaseInfo(
            version or "1.0", product.python, f"{product.package}=={version or '1.0'}"
        ),
    )


@pytest.fixture
def tab(qtbot, tmp_path):
    widget = McpTab(directory=tmp_path / "manager with spaces")
    qtbot.addWidget(widget)
    yield widget
    widget.shutdown()
    qtbot.waitUntil(
        lambda: QtCore.QThreadPool.globalInstance().activeThreadCount() == 0,
        timeout=10000,
    )


def _select(tab, key):
    for index in range(tab.product_select.count()):
        if tab.product_select.itemText(index) == PRODUCT_BY_KEY[key].name:
            tab.product_select.setCurrentIndex(index)
            return
    raise AssertionError(key)


@pytest.mark.parametrize("fails", [False, True])
def test_metadata_task_finishes_safely_after_qt_teardown(qapp, fails):
    import shiboken6

    calls = []

    def finish():
        calls.append(True)
        if fails:
            raise ValueError("Request finished after application shutdown")
        return ["1.0"]

    task = _Task(finish)
    shiboken6.delete(task.signals)
    task.run()
    assert calls == [True]


def test_environment_discovery_never_blocks_tab_selection(tab, qtbot, monkeypatch):
    release = threading.Event()
    started = threading.Event()
    calls = []
    gui_thread = threading.get_ident()

    def discover():
        calls.append(threading.get_ident())
        started.set()
        release.wait(5)
        return {}

    monkeypatch.setattr(installed_table, "find_all_python", discover)
    assert not calls  # Construction did not repeat host APM discovery.
    try:
        tab.show()
        qtbot.waitUntil(started.is_set)
        heartbeat = []
        QtCore.QTimer.singleShot(0, lambda: heartbeat.append(True))
        qtbot.waitUntil(lambda: bool(heartbeat))
        assert tab._discovery_pending
        assert calls == [calls[0]] and calls[0] != gui_thread
    finally:
        release.set()
    qtbot.waitUntil(lambda: not tab._discovery_pending)
    tab.hide()
    tab.show()
    assert len(calls) == 1


def test_ansys_python_discovery_is_hidden_and_bounded(monkeypatch):
    from ansys.tools.installer import find_python

    calls = []
    monkeypatch.setattr(
        find_python, "get_available_ansys_installations", lambda: {271: "ansys"}
    )
    monkeypatch.setattr(find_python, "ANSYS_SUPPORTED_PYTHON_VERSIONS", ["3_13"])
    monkeypatch.setattr(find_python.os.path, "exists", lambda path: True)
    monkeypatch.setattr(
        find_python.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False
    )
    monkeypatch.setattr(
        find_python.subprocess,
        "check_output",
        lambda *a, **k: calls.append(k) or "Python 3.13.15",
    )
    assert find_python._find_installed_ansys_python_win()
    assert calls == [{"text": True, "creationflags": 0x08000000, "timeout": 10}]


def test_previously_blank_vscode_destination_gets_a_personal_default(qtbot, tmp_path):
    (tmp_path / "settings.json").write_text(
        json.dumps({"pyaedt": {"client": "VS Code", "profile_path": ""}}),
        encoding="utf-8",
    )
    widget = McpTab(directory=tmp_path)
    qtbot.addWidget(widget)
    try:
        assert Path(widget.profile_path.text()).name == "mcp-config.json"
        assert widget.vscode_format.currentData() is False
    finally:
        widget.shutdown(save_settings=False)


def test_release_dropdown_automatic_cache_and_stale_results(tab, qtbot, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "ansys.tools.installer.mcp_tab.available_versions",
        lambda product: calls.append(product.key) or ["9.2", "9.1"],
    )
    tab.show()
    qtbot.waitUntil(lambda: tab.version.findText("9.2") >= 0)
    tab.version.requested.emit()
    assert calls == ["pyaedt"]
    tab.version.setCurrentText("9.1")
    tab._versions_fetched(("pymechanical", ["8.0"], None), None)
    assert tab.version.currentText() == "9.1" and tab.version.findText("8.0") < 0
    tab.source.setCurrentIndex(2)
    before = list(calls)
    tab.version.requested.emit()
    assert calls == before
    tab.source.setCurrentIndex(0)
    assert tab.version.currentText() == "9.1"


def test_installed_launch_controls_validate_and_invalidate_profile(tab, monkeypatch):
    monkeypatch.setattr(
        "ansys.tools.installer.mcp_tab.installed_version", lambda *args: "1.0"
    )
    signature = tab._launch_signature()
    schema = [
        dict(
            flags=["--static-tools"],
            kind="flag",
            nargs=0,
            choices=None,
            type="str",
            help="Use static tools",
            default=False,
        ),
        dict(
            flags=["--transport"],
            kind="value",
            nargs=None,
            choices=["stdio", "http"],
            type="str",
            help="Transport",
            default="stdio",
        ),
    ]
    tab._launch_loaded((signature, schema, None), None)
    assert tab.launch_choice.count() == 2  # Managed transport cannot be added twice.
    tab._add_launch_option(1)
    assert "--static-tools" in tab._arguments("stdio")
    tab._profile_preview = ("path", "old", "new")
    tab._remove_launch_option("--static-tools")
    assert tab._profile_preview is None
    _select(tab, "pymechanical")
    tab._launch_loaded((signature, schema, None), None)
    assert tab._launch_context is None


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
    assert tab.transport.currentData() == "stdio"
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


def _wheel(directory, version="0.0.0", requires_python=">=3.12"):
    """Create a solver-free console package for an actual offline pip install."""
    name = f"ansys_mechanical_mcp-{version}"
    files = {
        "apm_mcp_fixture.py": "def main():\n    print('fixture MCP')\n",
        f"{name}.dist-info/METADATA": f"Metadata-Version: 2.1\nName: ansys-mechanical-mcp\nVersion: {version}\nRequires-Python: {requires_python}\n",
        f"{name}.dist-info/WHEEL": "Wheel-Version: 1.0\nGenerator: apm-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        f"{name}.dist-info/entry_points.txt": "[console_scripts]\nansys-mechanical-mcp = apm_mcp_fixture:main\n",
    }
    files[f"{name}.dist-info/RECORD"] = "".join(f"{path},,\n" for path in files)
    directory.mkdir(parents=True, exist_ok=True)
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
    tab.select_python(sys.executable)
    tab.source.setCurrentIndex(2)
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
    tab._review_or_write_profile()
    assert "pymechanical-mcp" not in configuration.read_text()
    assert tab.write_profile_button.isEnabled()
    assert tab.write_profile_button.text() == "Save reviewed configuration"
    tab._review_or_write_profile()
    data = json.loads(configuration.read_text())["mcpServers"]
    assert data["existing"]["command"] == "keep"
    assert data["pymechanical-mcp"]["env"] == {"EXAMPLE": "value"}
    assert list(configuration.parent.glob("*.bak"))
    tab._preview_profile()
    tab.extra.setPlainText('["--static-tools"]')
    assert tab._profile_preview is None
    assert tab.write_profile_button.text() == "Review configuration…"
    assert "Review the changes" not in tab.status.text()


def test_invalid_install_source_shows_error_without_starting(tab):
    tab.source.setCurrentIndex(1)
    tab.branch.setText("main#bad")
    tab._try(lambda: tab._install(False))
    assert "Git branch" in tab.status.text()
    assert not tab.queue.active


def test_uses_the_same_apm_selector_widgets(tab):
    assert isinstance(tab.python_select, installed_table.DataComboBox)
    assert tab.python_select.installed_python and tab.python_select.installed_forge
    assert isinstance(tab.environment_select, installed_table.DataComboBox)
    assert tab.environment_select.created_venv


def test_source_options_and_advanced_controls_are_progressive(tab):
    assert not tab.install_advanced_toggle.isChecked()
    assert not tab.server_advanced_toggle.isChecked()
    assert tab.preview_section.isHidden()
    assert tab.branch.isHidden() and tab.wheelhouse_row.isHidden()
    tab.source.setCurrentIndex(1)
    assert not tab.branch.isHidden()
    assert tab.version_row.isHidden() and tab.wheelhouse_row.isHidden()
    tab.source.setCurrentIndex(2)
    assert tab.branch.isHidden()
    assert not tab.wheelhouse_row.isHidden() and not tab.version_row.isHidden()
    assert not hasattr(tab, "versions_button")


def test_missing_saved_python_path_does_not_grow_on_refresh(tab, tmp_path):
    missing = str(tmp_path / "removed" / "python.exe")
    tab.select_python(missing)
    tab._select_path(tab.python_select, missing)
    assert tab._base_python() == missing
    tab._refresh_choices()
    tab._select_path(tab.python_select, missing)
    assert tab._base_python() == missing


def test_discovered_directory_named_python_is_not_treated_as_an_executable(
    tab, tmp_path
):
    directory = tmp_path / "python"
    executable = mcp_backend.python_executable(directory)
    executable.parent.mkdir(parents=True)
    executable.touch()
    assert tab._python_choice(directory) == str(executable)


def test_exact_release_updates_python_choices_dynamically(
    tab, qtbot, tmp_path, monkeypatch
):
    from ansys.tools.installer import mcp_compatibility
    from ansys.tools.installer.mcp_releases import PythonInfo

    versions = ("3.13.4", "3.13.8", "3.14.2")
    paths = [
        tmp_path / version / ("python.exe" if sys.platform == "win32" else "python")
        for version in versions
    ]
    for path in paths:
        path.parent.mkdir()
        path.touch()
    inventory = {str(path): (version, False) for path, version in zip(paths, versions)}
    monkeypatch.setattr(installed_table, "find_all_python", lambda: inventory)
    monkeypatch.setattr(
        mcp_compatibility,
        "inspect_python",
        lambda path: PythonInfo(
            path, versions[[str(p) for p in paths].index(path)], 64
        ),
    )
    monkeypatch.setattr(
        mcp_backend,
        "published_release",
        lambda product, version="": ReleaseInfo(
            version or "1.0",
            ">=3.14,<3.15" if version == "2.0" else ">=3.13.5,<3.14",
            product.package,
        ),
    )
    tab._manual_pythons.clear()
    tab._refresh_choices()
    tab.show()
    qtbot.waitUntil(lambda: tab._compatibility is not None, timeout=10000)
    assert tab._base_python() == str(paths[1])
    assert not tab.python_select.model().item(0).isEnabled()
    assert tab.python_select.model().item(1).isEnabled()
    assert not tab.python_select.model().item(2).isEnabled()
    tab.version.setCurrentText("2.0")
    qtbot.waitUntil(
        lambda: tab._compatibility is not None
        and tab._compatibility.release.version == "2.0",
        timeout=10000,
    )
    assert tab._base_python() == str(paths[2])
    assert tab.python_select.model().item(2).isEnabled()
    assert not tab.python_select.model().item(1).isEnabled()


def test_late_compatibility_response_cannot_replace_current_selection(tab):
    from ansys.tools.installer.mcp_compatibility import Compatibility

    revision = tab._compatibility_revision
    stale = Compatibility(ReleaseInfo("old", ">=3.13", "old"), {}, {}, {})
    tab.version.setCurrentText("2.0")
    tab._compatibility_checked((revision, stale, ""), None)
    assert tab._compatibility is None
    assert tab.version.currentText() == "2.0"


def test_incompatible_existing_environment_is_not_silently_retargeted(
    tab, qtbot, tmp_path, monkeypatch
):
    from ansys.tools.installer import mcp_compatibility
    from ansys.tools.installer.mcp_releases import PythonInfo

    root = tmp_path / "selected-existing"
    executable = mcp_backend.python_executable(root)
    executable.parent.mkdir(parents=True)
    executable.touch()
    marker = root / "pyvenv.cfg"
    marker.write_text("preserved")
    real_probe = mcp_compatibility.inspect_python
    monkeypatch.setattr(
        mcp_compatibility,
        "inspect_python",
        lambda path: (
            PythonInfo(path, "3.12.9", 64)
            if path == str(executable)
            else real_probe(path)
        ),
    )
    tab.select_environment(root)
    tab.show()
    qtbot.waitUntil(lambda: tab._compatibility is not None, timeout=10000)
    assert tab.environment == root
    assert not tab.install_button.isEnabled()
    assert "Select a supported" in tab.python_hint.text()
    assert marker.read_text() == "preserved"


def test_coding_agent_connection_defaults_and_workspace_choice(
    tab, monkeypatch, tmp_path
):
    tab.client.setCurrentText("VS Code")
    assert Path(tab.profile_path.text()).name == "mcp-config.json"
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getExistingDirectory",
        lambda *args: str(tmp_path),
    )
    tab.vscode_format.setCurrentIndex(1)
    tab._browse_workspace()
    assert Path(tab.profile_path.text()) == tmp_path / ".vscode/mcp.json"
    tab.transport.setCurrentIndex(1)
    assert tab._transport() == "http"
    tab.client.setCurrentText("Claude Desktop")
    assert tab.transport.count() == 1 and tab._transport() == "stdio"


def test_existing_dedicated_environment_displays_its_actual_python(
    tab, qtbot, monkeypatch
):
    from ansys.tools.installer import mcp_compatibility
    from ansys.tools.installer.mcp_releases import PythonInfo

    executable = mcp_backend.python_executable(tab.environment)
    executable.parent.mkdir(parents=True)
    executable.touch()
    real_probe = mcp_compatibility.inspect_python
    monkeypatch.setattr(
        mcp_compatibility,
        "inspect_python",
        lambda path: (
            PythonInfo(path, "3.13.9", 64)
            if path == str(executable)
            else real_probe(path)
        ),
    )
    tab.show()
    qtbot.waitUntil(lambda: tab._compatibility is not None, timeout=10000)
    assert "3.13.9" in tab.managed_python_info.text()
    assert tab.python_select.isHidden()
    assert tab.python_caption.text() == "Python version"


def test_actions_stay_visible_with_logs_and_previews(tab, qtbot):
    tab.resize(660, 560)
    tab.show()
    tab.log_group.setChecked(True)
    for index, buttons in (
        (0, (tab.install_button, tab.save_button)),
        (1, (tab.start_button, tab.server_save_button)),
        (2, (tab.write_profile_button,)),
    ):
        tab.pages.setCurrentIndex(index)
        if index == 2:
            tab.preview_section.show()
        qtbot.wait(20)
        assert tab.action_stack.currentIndex() == index
        for button in buttons:
            assert button.isVisible()
            point = button.mapTo(tab, QtCore.QPoint(0, 0))
            assert tab.rect().contains(QtCore.QRect(point, button.size()))


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
    tab.select_environment(existing)
    tab.source.setCurrentIndex(2)
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
        tab.select_environment(root)
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


def test_latest_is_default_for_every_product(tab):
    for index in range(tab.product_select.count()):
        tab.product_select.setCurrentIndex(index)
        assert tab.version.currentText() == "Latest"
        assert tab._version() == ""


@pytest.mark.skipif(sys.version_info < (3, 12), reason="MCP interpreter baseline")
def test_latest_offline_install_upgrades_existing_package(tab, qtbot, tmp_path):
    _select(tab, "pymechanical")
    wheels = tmp_path / "wheels"
    _wheel(wheels, "0.0.0")
    tab.source.setCurrentIndex(2)
    tab.wheelhouse_path.setText(str(wheels))
    tab.select_python(sys.executable)
    tab._install(False)
    qtbot.waitUntil(lambda: not tab._preparing and not tab.queue.active, timeout=90000)
    assert (
        installed_version(tab.environment, tab.product) == "0.0.0"
    ), tab.log.toPlainText()
    _wheel(wheels, "0.0.1")
    tab._install(False)
    qtbot.waitUntil(lambda: not tab._preparing and not tab.queue.active, timeout=90000)
    assert (
        installed_version(tab.environment, tab.product) == "0.0.1"
    ), tab.log.toPlainText()
    assert "--upgrade" in tab.log.toPlainText()


@pytest.mark.skipif(sys.version_info < (3, 12), reason="MCP interpreter baseline")
def test_dynamic_selector_checks_release_without_creating_environment(
    tab, qtbot, tmp_path
):
    _select(tab, "pymechanical")
    wheels = tmp_path / "wheels"
    _wheel(wheels)
    tab.source.setCurrentIndex(2)
    tab.wheelhouse_path.setText(str(wheels))
    tab.show()
    qtbot.waitUntil(lambda: tab._compatibility is not None, timeout=10000)
    assert "Selected Python" in tab.python_hint.text(), tab.status.text()
    assert not tab.environment.exists()
    assert not tab.queue.active

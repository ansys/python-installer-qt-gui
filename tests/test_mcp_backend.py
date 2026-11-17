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
from types import MethodType, SimpleNamespace
import zipfile

import pytest

from ansys.tools.installer import mcp_backend as backend
from ansys.tools.installer.mcp_catalog import PRODUCT_BY_KEY, PRODUCTS
from ansys.tools.installer.mcp_releases import PythonInfo


@pytest.mark.parametrize("product", PRODUCTS, ids=lambda product: product.key)
def test_launch_contract(product):
    if product.key == "pylumerical":
        assert backend.server_arguments(product) == []
        with pytest.raises(ValueError, match="stdio only"):
            backend.server_arguments(product, "http")
    else:
        assert backend.server_arguments(product) == ["--transport", "stdio"]
        host, port = (
            ("--host", "--port")
            if product.key in ("pyfluent", "pycfx")
            else ("--http-host", "--http-port")
        )
        assert backend.server_arguments(product, "http", 9001) == [
            "--transport",
            "http",
            host,
            "127.0.0.1",
            port,
            "9001",
        ]


@pytest.mark.parametrize(
    "extra", [["--transport=http"], ["--http-port", "9"], ["--host=0.0.0.0"]]
)
def test_transport_cannot_be_overridden(extra):
    with pytest.raises(ValueError):
        backend.server_arguments(PRODUCT_BY_KEY["pyfluent"], extra=extra)


def test_solver_port_is_distinct_from_http_port():
    args = backend.server_arguments(PRODUCTS[0], "http", 8080, ["--port", "50051"])
    assert args[-2:] == ["--port", "50051"]
    assert args[args.index("--http-port") + 1] == "8080"


def test_requirement_rejects_injection_and_preserves_branch():
    product = PRODUCTS[0]
    assert (
        backend.package_requirement(product, version="0.2.0") == "ansys-aedt-mcp==0.2.0"
    )
    assert backend.package_requirement(
        product, "branch", branch="feature/new-ui"
    ).endswith("https://github.com/ansys/pyaedt-mcp.git@feature/new-ui")
    for branch in ("main#egg=other", "--help", "main; calc", "main@evil", ""):
        with pytest.raises(ValueError):
            backend.package_requirement(product, "branch", branch=branch)
    with pytest.raises(ValueError):
        backend.package_requirement(product, version="1 --extra-index-url http://evil")


def test_install_plan_targets_environment_and_checks_dependencies(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        backend, "inspect_python", lambda path: PythonInfo(str(path), "3.13.1", 64)
    )
    root = tmp_path / "env with spaces"
    commands = backend.installation_commands(
        PRODUCTS[1], root, sys.executable, "ansys-mechanical-mcp", upgrade=True
    )
    assert not root.exists()
    assert commands[1] == [sys.executable, "-I", "-m", "venv", str(root)]
    assert commands[-2][0] == str(backend.python_executable(root))
    assert "--upgrade" in commands[-2]
    assert commands[-1][-2:] == ["pip", "check"]
    probe = subprocess.run(commands[0], capture_output=True)
    assert (probe.returncode == 0) == (sys.version_info[:3] == (3, 13, 1))


def test_install_rejects_non_environment_even_when_python_present(tmp_path):
    root = tmp_path / "system"
    root.mkdir()
    python = backend.python_executable(root)
    python.parent.mkdir(exist_ok=True)
    python.touch()
    with pytest.raises(ValueError, match="not an environment"):
        backend.installation_commands(PRODUCTS[0], root, sys.executable, "pkg")
    with pytest.raises(ValueError, match="not a system Python"):
        backend.installation_commands(
            PRODUCTS[0], root, sys.executable, "pkg", custom=True
        )


def test_offline_plan_never_uses_index_or_git(tmp_path, monkeypatch):
    monkeypatch.setattr(
        backend, "inspect_python", lambda path: PythonInfo(str(path), "3.13.1", 64)
    )
    commands = backend.installation_commands(
        PRODUCTS[1],
        tmp_path / "env",
        sys.executable,
        "ansys-mechanical-mcp",
        offline=tmp_path,
    )
    assert commands[-2][-4:] == [
        "--no-index",
        "--find-links",
        str(tmp_path),
        "ansys-mechanical-mcp",
    ]
    with pytest.raises(ValueError, match="not Git"):
        backend.installation_commands(
            PRODUCTS[1],
            tmp_path / "env",
            sys.executable,
            "pkg @ git+https://github.com/ansys/pkg",
            offline=tmp_path,
        )


@pytest.mark.parametrize("filename", ["../escape.whl", "/escape.whl", "..\\escape.whl"])
def test_unsafe_zip_rejected_before_extraction(tmp_path, filename):
    archive = tmp_path / "wheels.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("good.whl", "ok")
        stream.writestr(filename, "bad")
    destination = tmp_path / "extracted"
    with pytest.raises(ValueError, match="unsafe"):
        backend.prepare_wheelhouse(archive, destination)
    assert not destination.exists()


def test_wheelhouse_and_metadata(tmp_path):
    archive = tmp_path / "wheels.zip"
    with zipfile.ZipFile(archive, "w") as stream:
        stream.writestr("example.whl", "example")
    target = backend.prepare_wheelhouse(archive, tmp_path / "wheels")
    assert (target / "example.whl").read_text() == "example"
    metadata = (
        tmp_path
        / "env/lib/python3.13/site-packages/ansys_aedt_mcp-1.0.dist-info/METADATA"
    )
    metadata.parent.mkdir(parents=True)
    metadata.write_text("Name: ansys-aedt-mcp\nVersion: 1.0\n", encoding="utf-8")
    assert backend.installed_version(tmp_path / "env", PRODUCTS[0]) == "1.0"


def test_platform_paths_and_symlinks(tmp_path):
    assert (
        backend.python_executable(tmp_path, windows=True)
        == tmp_path / "Scripts/python.exe"
    )
    assert backend.python_executable(tmp_path, windows=False) == tmp_path / "bin/python"
    assert (
        backend.console_executable(tmp_path, PRODUCTS[0], windows=True).name
        == "ansys-aedt-mcp.exe"
    )
    assert (
        backend.console_executable(tmp_path, PRODUCTS[0], windows=False)
        == tmp_path / "bin/ansys-aedt-mcp"
    )


def test_settings_round_trip_and_corruption(tmp_path):
    path = tmp_path / "settings.json"
    backend.atomic_write(path, json.dumps({"pyaedt": {"version": "0.2.0"}}))
    assert backend.read_settings(path)["pyaedt"]["version"] == "0.2.0"
    path.write_text("[]")
    with pytest.raises(ValueError):
        backend.read_settings(path)
    assert path.read_text() == "[]"


def test_pypi_versions_exclude_yanked_and_prereleases(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "releases": {
                    "1.0": [{"yanked": False}],
                    "2.0": [{"yanked": True}],
                    "3.0rc1": [{}],
                    "0.9": [],
                    "0.8": [{}],
                }
            }

    def get(url, timeout):
        assert url == "https://pypi.org/pypi/ansys-aedt-mcp/json"
        assert timeout == 20
        return Response()

    monkeypatch.setattr(backend.requests, "get", get)
    assert backend.available_versions(PRODUCTS[0]) == ["1.0", "0.8"]


def test_remove_settings_preserves_mcp_environments(monkeypatch, tmp_path):
    from ansys.tools.installer import uninstall

    root = tmp_path / "manager"
    environment = root / "mcp/environments/pyaedt"
    environment.mkdir(parents=True)
    marker = environment / "pyvenv.cfg"
    marker.write_text("home = example")
    for filename in ("config.json", "history.json", "mcp/settings.json"):
        (root / filename).write_text("{}")
    monkeypatch.setattr(
        uninstall, "ConfigureJson", lambda: SimpleNamespace(config_dir=root)
    )
    uninstall.Uninstall._remove_configs(SimpleNamespace())
    assert marker.exists()
    assert not (root / "mcp/settings.json").exists()
    assert not (root / "config.json").exists()


def test_remove_managed_environments_includes_mcp_only_when_requested(
    monkeypatch, tmp_path
):
    from ansys.tools.installer import uninstall

    mcp = tmp_path / "mcp"
    environment = mcp / "environments/pyaedt"
    (environment / "bin").mkdir(parents=True)
    (environment / "bin/activate").touch()
    external = tmp_path / "external environment"
    external.mkdir()
    monkeypatch.setattr(
        uninstall,
        "ConfigureJson",
        lambda: SimpleNamespace(history={"path": [str(tmp_path / "missing")]}),
    )
    monkeypatch.setattr(uninstall, "application_directory", lambda: mcp)
    monkeypatch.setattr(uninstall, "is_linux_os", lambda: True)
    uninstall.Uninstall._remove_all_venvs(SimpleNamespace())
    assert not environment.exists()
    assert external.exists()


def test_existing_package_manager_cannot_mutate_busy_mcp_environment(
    tmp_path, monkeypatch
):
    from ansys.tools.installer import installed_table

    root = tmp_path / "busy MCP environment"
    errors = []
    parent = SimpleNamespace(
        mcp_tab=SimpleNamespace(environment_in_use=lambda path: str(path) == str(root)),
        show_error=errors.append,
    )
    widget = SimpleNamespace(
        _parent=parent,
        is_chk_box_active=lambda: False,
        venv_table=SimpleNamespace(active_path=str(root / "Scripts")),
    )
    widget._mcp_operation_blocks_changes = MethodType(
        installed_table.InstalledTab._mcp_operation_blocks_changes, widget
    )
    monkeypatch.setattr(
        installed_table.subprocess,
        "call",
        lambda *args, **kwargs: pytest.fail("Must not start a competing installer"),
    )
    installed_table.InstalledTab.launch_cmd(widget, "uv pip install numpy")
    assert len(errors) == 1
    assert "Stop the MCP server" in errors[0]

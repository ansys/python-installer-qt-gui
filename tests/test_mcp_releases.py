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

from pathlib import Path
import sys
import zipfile

import pytest
import requests

from ansys.tools.installer import mcp_backend as backend
from ansys.tools.installer import mcp_releases as releases
from ansys.tools.installer.mcp_catalog import PRODUCT_BY_KEY, PRODUCTS
from ansys.tools.installer.mcp_releases import PythonInfo, ReleaseInfo


class Response:
    def __init__(self, data=None, text=""):
        self.data = data
        self.text = text

    def raise_for_status(self):
        pass

    def json(self):
        return self.data


def test_latest_is_resolved_again_and_pinned_exactly(monkeypatch):
    product = PRODUCTS[0]
    versions = iter(["1.0.0", "1.0.1"])
    calls = []

    def get(url, timeout):
        calls.append(url)
        assert timeout == 20
        return Response(
            {
                "info": {
                    "name": product.package,
                    "version": next(versions),
                    "requires_python": ">=3.13,<3.15",
                },
                "urls": [{"yanked": False}],
            }
        )

    monkeypatch.setattr(releases.requests, "get", get)
    assert releases.published_release(product).requirement == "ansys-aedt-mcp==1.0.0"
    assert releases.published_release(product).requirement == "ansys-aedt-mcp==1.0.1"
    assert calls == ["https://pypi.org/pypi/ansys-aedt-mcp/json"] * 2


def test_yanked_or_wrong_package_cannot_be_selected(monkeypatch):
    product = PRODUCTS[0]
    data = {
        "info": {"name": product.package, "version": "1.0"},
        "urls": [{"yanked": True}],
    }
    monkeypatch.setattr(
        releases.requests, "get", lambda *args, **kwargs: Response(data)
    )
    with pytest.raises(ValueError, match="non-yanked"):
        releases.published_release(product)
    data["info"]["name"] = "unrelated-package"
    with pytest.raises(ValueError, match="different package"):
        releases.published_release(product)


@pytest.mark.parametrize(
    "key,version,supported",
    [
        ("pyaedt", "3.12.9", False),
        ("pyaedt", "3.13.1", True),
        ("pyaedt", "3.15.0", False),
        ("pymechanical", "3.11.9", False),
        ("pymechanical", "3.14.0", True),
        ("pymechanical", "3.15.0", False),
        ("pyfluent", "3.11.9", False),
        ("pyfluent", "3.12.0", True),
        ("pymapdl", "3.11.9", False),
        ("pymapdl", "3.14.0", True),
        ("pymapdl", "3.15.0", False),
        ("pylumerical", "3.10.9", False),
        ("pylumerical", "3.11.9", True),
        ("pycfx", "3.11.9", False),
        ("pycfx", "3.14.0", True),
        ("pycfx", "3.15.0", False),
    ],
)
def test_documented_python_ranges(key, version, supported):
    product = PRODUCT_BY_KEY[key]
    release = ReleaseInfo("1.0", ">=3.10,<4", "pkg==1.0")
    info = PythonInfo("python", version, 64)
    if supported:
        assert releases.validate_python(info, product, release) == info
    else:
        with pytest.raises(ValueError, match="requires 64-bit Python"):
            releases.validate_python(info, product, release)


def test_selected_release_constraints_override_broader_product_baseline():
    product = PRODUCT_BY_KEY["pyfluent"]
    release = ReleaseInfo("9.0", ">=3.13.4,!=3.13.5,<3.14", "pkg==9.0")
    for version in ("3.12.9", "3.13.3", "3.13.5", "3.14.0"):
        with pytest.raises(ValueError):
            releases.validate_python(
                PythonInfo("python", version, 64), product, release
            )
    releases.validate_python(PythonInfo("python", "3.13.6", 64), product, release)
    with pytest.raises(ValueError):
        releases.validate_python(PythonInfo("python", "3.13.6", 32), product, release)


def test_automatic_selection_keeps_supported_python_and_skips_incompatible(monkeypatch):
    product = PRODUCTS[0]
    release = ReleaseInfo("1.0", ">=3.13,<3.14", "pkg==1.0")
    versions = {"old": "3.12.9", "too-new": "3.14.0", "supported": "3.13.6"}
    monkeypatch.setattr(
        releases, "inspect_python", lambda path: PythonInfo(path, versions[path], 64)
    )
    assert (
        releases.compatible_python(
            product, release, "old", ["too-new", "supported"]
        ).executable
        == "supported"
    )
    assert (
        releases.compatible_python(product, release, "supported", ["old"]).executable
        == "supported"
    )


def test_source_uses_selected_branch_python_declaration(monkeypatch):
    def get(url, params, headers, timeout):
        assert (
            url
            == "https://api.github.com/repos/ansys/pyaedt-mcp/contents/pyproject.toml"
        )
        assert params == {"ref": "feature/new-python"}
        assert headers["Accept"] == "application/vnd.github.raw+json"
        return Response(
            text='[project]\nname="ansys-aedt-mcp"\nrequires-python=">=3.14,<3.15"\n'
        )

    monkeypatch.setattr(releases.requests, "get", get)
    assert (
        releases.source_release(
            PRODUCTS[0], "feature/new-python", "git-requirement"
        ).requires_python
        == ">=3.14,<3.15"
    )


def test_probe_reports_actual_python():
    info = releases.inspect_python(sys.executable)
    assert info.version == ".".join(str(part) for part in sys.version_info[:3])
    assert info.bits == 64
    assert Path(info.executable).is_absolute()


def test_newest_local_wheel_is_resolved_without_network(tmp_path, monkeypatch):
    product = PRODUCTS[0]
    monkeypatch.setattr(
        releases.requests,
        "get",
        lambda *args, **kwargs: pytest.fail("Offline must not access the network"),
    )
    for version in ("0.1.0", "0.2.0", "0.3.0rc1"):
        name = f"ansys_aedt_mcp-{version}"
        with zipfile.ZipFile(tmp_path / f"{name}-py3-none-any.whl", "w") as archive:
            archive.writestr(
                f"{name}.dist-info/METADATA",
                f"Name: {product.package}\nVersion: {version}\nRequires-Python: >=3.13\n",
            )
    assert releases.wheelhouse_release(product, tmp_path).version == "0.2.0"
    assert releases.wheelhouse_release(product, tmp_path, "0.1.0").version == "0.1.0"


def test_incompatible_existing_environment_is_preserved(tmp_path, monkeypatch):
    product = PRODUCTS[0]
    root = tmp_path / "existing"
    python = backend.python_executable(root)
    python.parent.mkdir(parents=True)
    python.touch()
    marker = root / "pyvenv.cfg"
    marker.write_text("keep")
    monkeypatch.setattr(
        backend,
        "published_release",
        lambda *args: ReleaseInfo("1.0", ">=3.13", "ansys-aedt-mcp==1.0"),
    )
    monkeypatch.setattr(
        backend, "inspect_python", lambda path: PythonInfo(str(path), "3.12.9", 64)
    )
    with pytest.raises(ValueError, match="existing environment was preserved"):
        backend.prepare_installation(product, root, sys.executable, custom=True)
    assert marker.read_text() == "keep"


def test_online_latest_failure_never_becomes_unpinned_install(tmp_path, monkeypatch):
    def fail(*args):
        raise requests.ConnectionError("offline")

    monkeypatch.setattr(backend, "published_release", fail)
    with pytest.raises(requests.ConnectionError):
        backend.prepare_installation(PRODUCTS[0], tmp_path / "new", sys.executable)
    assert not (tmp_path / "new").exists()


def test_online_latest_always_upgrades_even_from_install_button(tmp_path, monkeypatch):
    product = PRODUCTS[0]
    release = ReleaseInfo("9.0", ">=3.13", "ansys-aedt-mcp==9.0")
    interpreter = PythonInfo(sys.executable, "3.13.6", 64)
    monkeypatch.setattr(backend, "published_release", lambda *args: release)
    monkeypatch.setattr(backend, "compatible_python", lambda *args: interpreter)
    plan = backend.prepare_installation(product, tmp_path / "new", sys.executable)
    assert "--upgrade" in plan.commands[-2]
    assert plan.commands[-2][-1] == "ansys-aedt-mcp==9.0"


def test_manager_discovers_python_313_and_314_for_mcp_selection(monkeypatch):
    from ansys.tools.installer import find_python

    def output(command, text):
        if command[0] == "which" and command[1] in ("python3.13", "python3.14"):
            return f"/opt/managed/{command[1]}\n"
        if command[0] in ("/opt/managed/python3.13", "/opt/managed/python3.14"):
            return "Python " + command[0].rsplit("python", 1)[1] + ".1\n"
        raise FileNotFoundError(command[0])

    monkeypatch.setattr(find_python.subprocess, "check_output", output)
    result = find_python._find_installed_python_linux()
    assert result["/opt/managed/python3.13"][0] == "3.13.1"
    assert result["/opt/managed/python3.14"][0] == "3.14.1"

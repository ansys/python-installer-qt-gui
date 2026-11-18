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

import os
from pathlib import Path

from ansys.tools.installer import mcp_backend, mcp_compatibility
from ansys.tools.installer.mcp_catalog import PRODUCT_BY_KEY
from ansys.tools.installer.mcp_releases import PythonInfo, ReleaseInfo


def test_release_specific_requirements_and_actual_bitness(tmp_path, monkeypatch):
    product = PRODUCT_BY_KEY["pymechanical"]
    paths = [str(tmp_path / name) for name in ("old", "supported", "32bit")]
    for path in paths:
        Path(path).touch()
    monkeypatch.setattr(
        mcp_backend,
        "published_release",
        lambda *args: ReleaseInfo("2.0", ">=3.12.9,<3.14", product.package + "==2.0"),
    )
    monkeypatch.setattr(
        mcp_compatibility,
        "inspect_python",
        lambda path: PythonInfo(
            path,
            "3.12.8" if path == paths[0] else "3.13.1",
            32 if path == paths[2] else 64,
        ),
    )
    result = mcp_compatibility.check_compatibility(product, paths)
    assert list(result.interpreters) == [paths[1]]
    assert "3.12.8" in result.errors[paths[0]]
    assert "32-bit" in result.errors[paths[2]]
    assert result.release.version == "2.0"


def test_interpreter_cache_does_not_cache_latest_release(tmp_path, monkeypatch):
    product = PRODUCT_BY_KEY["pymechanical"]
    path = tmp_path / "python"
    path.touch()
    calls, probes = [], []

    def release(*args):
        calls.append(True)
        return ReleaseInfo(str(len(calls)), ">=3.12", product.package)

    def inspect(executable):
        probes.append(executable)
        return PythonInfo(executable, "3.13.1", 64)

    monkeypatch.setattr(mcp_backend, "published_release", release)
    monkeypatch.setattr(mcp_compatibility, "inspect_python", inspect)
    first = mcp_compatibility.check_compatibility(product, [str(path)])
    second = mcp_compatibility.check_compatibility(
        product, [str(path)], probes=first.probes
    )
    assert len(calls) == 2 and len(probes) == 1
    assert first.release.version != second.release.version
    previous = path.stat()
    path.write_text("changed executable")
    # A replacement can retain its timestamp, including on coarse filesystems.
    os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    mcp_compatibility.check_compatibility(product, [str(path)], probes=second.probes)
    assert len(probes) == 2


def test_unreadable_candidate_does_not_hide_supported_candidates(tmp_path, monkeypatch):
    product = PRODUCT_BY_KEY["pymechanical"]
    good = tmp_path / "good"
    good.touch()
    missing = tmp_path / "missing"
    monkeypatch.setattr(
        mcp_backend,
        "published_release",
        lambda *args: ReleaseInfo("1", ">=3.12", product.package),
    )
    monkeypatch.setattr(
        mcp_compatibility, "inspect_python", lambda path: PythonInfo(path, "3.13.1", 64)
    )
    result = mcp_compatibility.check_compatibility(product, [str(missing), str(good)])
    assert str(good) in result.interpreters
    assert str(missing) in result.errors

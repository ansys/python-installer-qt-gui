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

"""Validate installed-parser discovery and typed launch arguments."""

from dataclasses import replace
from pathlib import Path
import subprocess
import sys

import pytest

from ansys.tools.installer.mcp_catalog import PRODUCTS
from ansys.tools.installer.mcp_launch import launch_options, option_arguments


def test_inspection_exits_before_server_or_solver_start(tmp_path):
    root = tmp_path / "environment with spaces"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(root)], check=True
    )
    site = root / (
        "Lib/site-packages"
        if sys.platform == "win32"
        else f"lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
    )
    site.mkdir(parents=True, exist_ok=True)
    metadata = site / "fixture_mcp-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: fixture-mcp\nVersion: 1.0\n", encoding="utf-8"
    )
    (metadata / "entry_points.txt").write_text(
        "[console_scripts]\nfixture-mcp = fixture_mcp:main\n", encoding="utf-8"
    )
    marker = tmp_path / "server-started"
    (site / "fixture_mcp.py").write_text(
        "import argparse\nfrom pathlib import Path\n"
        "def main():\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_argument('--mode', choices=['one', 'two'], default='one')\n"
        "    parser.add_argument('--origins', nargs='+')\n"
        "    parser.add_argument('--enabled', action='store_true')\n"
        "    parser.add_argument('--count', type=int)\n"
        "    parser.parse_args()\n"
        f"    Path({str(marker)!r}).touch()\n",
        encoding="utf-8",
    )
    options = launch_options(root, replace(PRODUCTS[0], package="fixture-mcp"))
    assert not marker.exists()
    assert len(options) == 4
    assert option_arguments(
        options,
        {"--mode": "two", "--origins": ["a", "b"], "--enabled": True, "--count": "2"},
    ) == ["--mode", "two", "--origins", "a", "b", "--enabled", "--count", "2"]
    for values in (
        {"--unknown": "x"},
        {"--mode": "invalid"},
        {"--count": "abc"},
        {"--origins": []},
        {"--enabled": False},
    ):
        with pytest.raises(ValueError):
            option_arguments(options, values)


def test_lumerical_never_invokes_a_non_argparse_launcher(monkeypatch):
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: pytest.fail(
            "A stdio-only launcher must not be invoked for --help"
        ),
    )
    assert launch_options(Path("unused"), PRODUCTS[4]) == []

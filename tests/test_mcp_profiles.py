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

import pytest
import tomlkit

from ansys.tools.installer.mcp_catalog import PRODUCTS
from ansys.tools.installer.mcp_profiles import (
    CLIENTS,
    default_profile_path,
    render_profile,
    save_profile,
)


@pytest.mark.parametrize("client", CLIENTS)
def test_merge_preserves_other_mcp_and_settings(client, tmp_path):
    container = (
        "servers"
        if client == "VS Code"
        else "mcp" if client == "OpenCode" else "mcpServers"
    )
    original = (
        "# user comment\nmodel = 'example'\n[mcp_servers.other]\ncommand = 'keep'\n"
        if client == "Codex"
        else json.dumps({"setting": True, container: {"other": {"command": "keep"}}})
    )
    command = tmp_path / "path with spaces/ansys-aedt-mcp"
    rendered = render_profile(
        client, original, PRODUCTS[0], command, ["--transport", "stdio"]
    )
    if client == "Codex":
        data = tomlkit.parse(rendered)
        assert "# user comment" in rendered
        assert data["model"] == "example"
        servers = data["mcp_servers"]
    else:
        data = json.loads(rendered)
        assert data["setting"] is True
        servers = data[container]
    assert servers["other"] == {"command": "keep"}
    profile = servers["pyaedt-mcp"]
    if client == "OpenCode":
        assert profile["command"] == [str(command), "--transport", "stdio"]
    else:
        assert profile["command"] == str(command)
        assert profile["args"] == ["--transport", "stdio"]


def test_codex_replacement_removes_old_transport_and_env():
    original = """# retained
[mcp_servers.pyaedt-mcp]
command = 'old'
args = ['--old']
[mcp_servers.pyaedt-mcp.env]
OLD = 'value'
[mcp_servers.other]
command = 'keep'
"""
    rendered = render_profile(
        "Codex", original, PRODUCTS[0], "new", [], transport="http", port=9000
    )
    data = tomlkit.parse(rendered)
    assert data["mcp_servers"]["pyaedt-mcp"] == {
        "url": "http://127.0.0.1:9000/mcp",
        "startup_timeout_sec": 60,
    }
    assert data["mcp_servers"]["other"]["command"] == "keep"
    assert "# retained" in rendered


@pytest.mark.parametrize(
    "original", ["[]", '{"mcpServers": []}', '{"x":1,"x":2}', "{ // comment\n }"]
)
def test_invalid_json_not_overwritten(original):
    with pytest.raises(ValueError):
        render_profile("Cursor", original, PRODUCTS[0], "exe", [])


def test_claude_desktop_and_lumerical_transport_limits():
    with pytest.raises(ValueError, match="stdio"):
        render_profile("Claude Desktop", "", PRODUCTS[0], "exe", [], transport="http")
    with pytest.raises(ValueError, match="stdio"):
        render_profile("Cursor", "", PRODUCTS[4], "exe", [], transport="http")


def test_backups_and_concurrent_change(tmp_path):
    path = tmp_path / "mcp.json"
    original = '{"existing": true}'
    path.write_text(original)
    backup = save_profile(path, original, '{"updated":true}')
    assert backup.read_text() == original
    assert path.read_text() == '{"updated":true}'
    with pytest.raises(ValueError, match="changed since preview"):
        save_profile(path, original, "{}")
    assert path.read_text() == '{"updated":true}'


def test_client_paths_respect_platform_and_environment(tmp_path):
    assert (
        default_profile_path(
            "Claude Desktop", tmp_path, {"APPDATA": str(tmp_path / "roaming")}, True
        )
        == tmp_path / "roaming/Claude/claude_desktop_config.json"
    )
    assert (
        default_profile_path(
            "OpenCode", tmp_path, {"XDG_CONFIG_HOME": str(tmp_path / "xdg")}, False
        )
        == tmp_path / "xdg/opencode/opencode.json"
    )
    assert (
        default_profile_path(
            "Codex", tmp_path, {"CODEX_HOME": str(tmp_path / "codex")}, False
        )
        == tmp_path / "codex/config.toml"
    )

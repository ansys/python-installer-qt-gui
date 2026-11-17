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

"""Preview and merge MCP profiles without replacing unrelated client settings."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil

import tomlkit

from ansys.tools.installer.mcp_backend import atomic_write

CLIENTS = ("VS Code", "Copilot CLI", "Claude Desktop", "Cursor", "Codex", "OpenCode")


def default_profile_path(client, home=None, environ=None, windows=None):
    """Return platform-specific client paths; VS Code uses a chosen workspace."""
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    windows = os.name == "nt" if windows is None else windows
    config = Path(environ.get("XDG_CONFIG_HOME") or home / ".config")
    paths = {
        "VS Code": home / ".vscode" / "mcp.json",
        "Copilot CLI": home / ".copilot" / "mcp-config.json",
        "Claude Desktop": (
            Path(environ.get("APPDATA") or home / "AppData" / "Roaming")
            if windows
            else config
        )
        / "Claude"
        / "claude_desktop_config.json",
        "Cursor": home / ".cursor" / "mcp.json",
        "Codex": Path(environ.get("CODEX_HOME") or home / ".codex") / "config.toml",
        "OpenCode": config / "opencode" / "opencode.json",
    }
    return paths[client]


def _unique_object(pairs):
    data = {}
    for key, value in pairs:
        if key in data:
            raise ValueError(f"Duplicate JSON key: {key}")
        data[key] = value
    return data


def render_profile(
    client, original, product, executable, arguments, *, transport="stdio", port=8080
):
    """Return a merged JSON/TOML document for review before installation."""
    if client not in CLIENTS:
        raise ValueError("Unknown MCP client.")
    if transport not in ("stdio", "http"):
        raise ValueError("Unknown MCP transport.")
    if transport == "http" and product.http_flags is None:
        raise ValueError(f"{product.name} only supports stdio.")
    if transport == "http" and client == "Claude Desktop":
        raise ValueError("Use stdio for Claude Desktop's local configuration file.")
    url = f"http://127.0.0.1:{port}/mcp"
    key = f"{product.key}-mcp"
    command = str(executable)
    if client == "Codex":
        data = tomlkit.parse(original)
        servers = data.setdefault("mcp_servers", tomlkit.table())
        if not isinstance(servers, dict):
            raise ValueError("mcp_servers must be a TOML table.")
        servers[key] = (
            {"url": url}
            if transport == "http"
            else {"command": command, "args": list(arguments)}
        )
        servers[key]["startup_timeout_sec"] = 60
        return tomlkit.dumps(data)
    data = (
        json.loads(original, object_pairs_hook=_unique_object)
        if original.strip()
        else {}
    )
    if not isinstance(data, dict):
        raise ValueError("The client configuration must contain a JSON object.")
    container = (
        "servers"
        if client == "VS Code"
        else "mcp" if client == "OpenCode" else "mcpServers"
    )
    servers = data.setdefault(container, {})
    if not isinstance(servers, dict):
        raise ValueError(f"The {container} section must contain a JSON object.")
    if client == "OpenCode":
        profile = (
            {"type": "remote", "url": url}
            if transport == "http"
            else {"type": "local", "command": [command, *arguments]}
        )
    elif transport == "http":
        profile = {"type": "http", "url": url}
    else:
        profile = {"command": command, "args": list(arguments)}
        if client == "VS Code":
            profile["type"] = "stdio"
        elif client == "Copilot CLI":
            profile["type"] = "local"
    if client == "Copilot CLI":
        profile["tools"] = ["*"]
    servers[key] = profile
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def save_profile(path, original, rendered):
    """Back up and atomically save only if the file still matches its preview."""
    path = Path(path)
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    if current != original:
        raise ValueError(
            "Configuration changed since preview. Preview it again before saving."
        )
    backup = None
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup = path.with_name(f"{path.name}.{stamp}.bak")
        shutil.copy2(path, backup)
    atomic_write(path, rendered)
    return backup

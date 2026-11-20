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
    """Return each agent's personal configuration, respecting its home override."""
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    windows = os.name == "nt" if windows is None else windows
    config = Path(environ.get("XDG_CONFIG_HOME") or home / ".config")
    paths = {
        "VS Code": Path(environ.get("COPILOT_HOME") or home / ".copilot")
        / "mcp-config.json",
        "Copilot CLI": Path(environ.get("COPILOT_HOME") or home / ".copilot")
        / "mcp-config.json",
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


def _profile_keys(servers, product):
    def normalized(name):
        return "".join(char for char in name.casefold() if char.isalnum())

    aliases = {
        normalized(name)
        for name in (
            product.key,
            f"{product.key}-mcp",
            product.package,
            product.package.removeprefix("ansys-"),
        )
    }
    keys = [key for key in servers if normalized(key) in aliases]
    if keys:
        canonical = f"{product.key}-mcp"
        return sorted(keys, key=lambda key: key != canonical)
    module = product.package.replace("-", ".")
    for key, value in servers.items():
        if not isinstance(value, dict):
            continue
        command = value.get("command", "")
        argv = (
            [*command]
            if isinstance(command, list)
            else [command, *value.get("args", [])]
        )
        launcher = any(
            isinstance(token, str)
            and token.replace("\\", "/").rsplit("/", 1)[-1].removesuffix(".exe")
            == product.package
            for token in argv
        )
        module_launch = any(
            argv[i : i + 2] == ["-m", module] for i in range(len(argv) - 1)
        )
        if launcher or module_launch:
            keys.append(key)
    if len(keys) > 1:
        raise ValueError(
            f"Multiple custom configurations launch {product.name}. Select or consolidate the intended entry in the file before reviewing; no changes were made."
        )
    return keys


def _merge_missing(target, source):
    for key, value in source.items():
        if key not in target:
            target[key] = value
        elif isinstance(target[key], dict) and isinstance(value, dict):
            _merge_missing(target[key], value)


def _server_container(data, client, vscode_legacy=False):
    name = (
        "mcp_servers"
        if client == "Codex"
        else (
            "servers"
            if client == "VS Code" and vscode_legacy
            else "mcp" if client == "OpenCode" else "mcpServers"
        )
    )
    servers = data.setdefault(name, tomlkit.table() if client == "Codex" else {})
    if not isinstance(servers, dict):
        raise ValueError(f"{name} must contain an object/table.")
    if client == "OpenCode":
        # Existing V1 files retain their layout; new files use the V2 schema.
        legacy = any(
            key != "servers"
            and isinstance(value, dict)
            and (
                value.get("type") in ("local", "remote")
                or "command" in value
                or "url" in value
            )
            for key, value in servers.items()
        )
        if "servers" in servers and legacy:
            raise ValueError(
                "OpenCode configuration mixes V1 and V2 layouts. Migrate it before reviewing; no changes were made."
            )
        if not legacy:
            servers = servers.setdefault("servers", {})
            if not isinstance(servers, dict):
                raise ValueError("mcp.servers must contain an object.")
    return servers


def render_profile(
    client,
    original,
    product,
    executable,
    arguments,
    *,
    transport="stdio",
    port=8080,
    vscode_legacy=False,
    environment=None,
):
    """Merge a single product while preserving other servers and user preferences."""
    if client not in CLIENTS:
        raise ValueError("Unknown MCP client.")
    if transport not in ("stdio", "http"):
        raise ValueError("Unknown MCP transport.")
    if transport == "http" and product.http_flags is None:
        raise ValueError(f"{product.name} only supports stdio.")
    if transport == "http" and client == "Claude Desktop":
        raise ValueError("Use stdio for Claude Desktop's local configuration file.")
    data = (
        tomlkit.parse(original)
        if client == "Codex"
        else (
            json.loads(original, object_pairs_hook=_unique_object)
            if original.strip()
            else {}
        )
    )
    if not isinstance(data, dict):
        raise ValueError("The client configuration must contain an object.")
    servers = _server_container(data, client, vscode_legacy)
    matches = _profile_keys(servers, product)
    key = matches[0] if matches else f"{product.key}-mcp"
    profile = servers.setdefault(key, tomlkit.table() if client == "Codex" else {})
    if not isinstance(profile, dict):
        raise ValueError(f"The existing {key} entry must contain an object/table.")
    for duplicate in matches[1:]:
        if not isinstance(servers[duplicate], dict):
            raise ValueError(
                f"The existing {duplicate} entry must contain an object/table."
            )
        _merge_missing(profile, servers[duplicate])
        del servers[duplicate]
    if transport == "stdio":
        for field in (
            "url",
            "headers",
            "http_headers",
            "env_http_headers",
            "bearer_token_env_var",
            "oauth",
            "type",
        ):
            profile.pop(field, None)
        profile["command"] = (
            [str(executable), *arguments] if client == "OpenCode" else str(executable)
        )
        if client == "OpenCode":
            profile.pop("args", None)
            profile["type"] = "local"
        else:
            profile["args"] = list(arguments)
            if client in ("VS Code", "Copilot CLI"):
                profile["type"] = "local" if client == "Copilot CLI" else "stdio"
        if environment:
            field = "environment" if client == "OpenCode" else "env"
            overrides = profile.setdefault(field, {})
            if not isinstance(overrides, dict):
                raise ValueError(f"{key}.{field} must contain an object/table.")
            overrides.update(environment)
    else:
        for field in (
            "command",
            "args",
            "env",
            "environment",
            "env_vars",
            "cwd",
            "type",
        ):
            profile.pop(field, None)
        profile["url"] = f"http://127.0.0.1:{port}/mcp"
        if client in ("VS Code", "Copilot CLI", "OpenCode"):
            profile["type"] = "remote" if client == "OpenCode" else "http"
    if client == "Codex":
        profile.setdefault("startup_timeout_sec", 60)
        return tomlkit.dumps(data)
    if client == "Copilot CLI":
        profile.setdefault("tools", ["*"])
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

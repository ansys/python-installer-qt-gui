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

"""Installation plans and persistent settings independent of the Qt UI."""

from dataclasses import dataclass
from email.parser import Parser
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

from packaging.version import Version
import requests

from ansys.tools.installer.mcp_releases import (
    PythonInfo,
    ReleaseInfo,
    compatible_python,
    inspect_python,
    published_release,
    source_release,
    validate_python,
    wheelhouse_release,
)


def application_directory():
    """Return the manager's per-user MCP configuration directory."""
    return Path.home() / ".ansys" / "ansys_python_manager" / "mcp"


def atomic_write(path, content):
    """Replace a text file atomically, using private permissions for new files."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_settings(path):
    """Read saved settings, refusing to silently replace a damaged file."""
    if not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(
        not isinstance(value, dict) for value in data.values()
    ):
        raise ValueError(f"Invalid MCP settings: {path}")
    return data


def python_executable(directory, windows=None):
    """Find Python in a virtual environment, conda environment or scripts folder."""
    root = Path(directory).expanduser().absolute()
    if root.is_file():
        return root
    windows = os.name == "nt" if windows is None else windows
    candidates = (
        [root / "Scripts" / "python.exe", root / "python.exe"]
        if windows
        else [root / "bin" / "python", root / "python", root / "python3"]
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


def console_executable(directory, product, windows=None):
    """Return the installed console script without resolving venv symlinks."""
    windows = os.name == "nt" if windows is None else windows
    root = Path(directory).expanduser().absolute()
    return (
        root
        / ("Scripts" if windows else "bin")
        / (product.package + (".exe" if windows else ""))
    )


def installed_version(directory, product):
    """Read distribution metadata without importing the MCP or its solver."""
    root = Path(directory)
    paths = [root / "Lib" / "site-packages"]
    paths.extend(root.glob("lib*/python*/site-packages"))
    name = product.package.replace("-", "_")
    for site in paths:
        for metadata in site.glob(f"{name}-*.dist-info/METADATA"):
            message = Parser().parsestr(metadata.read_text(encoding="utf-8"))
            if message.get("Version"):
                return message["Version"]
    return None


def package_requirement(product, source="release", version="", branch="main"):
    """Build one pip requirement using only an official product repository."""
    if source == "branch":
        if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_./-]*", branch):
            raise ValueError(
                "Enter a Git branch, tag or commit without URL characters."
            )
        return f"{product.package} @ git+{product.repository}.git@{branch}"
    if source != "release":
        raise ValueError("Unknown installation source.")
    return f"{product.package}=={Version(version)}" if version else product.package


def prepare_wheelhouse(source, destination):
    """Use a wheel directory or safely extract a wheelhouse ZIP without links."""
    source = Path(source).expanduser()
    if source.is_dir():
        return source.absolute()
    if not source.is_file() or source.suffix.lower() != ".zip":
        raise ValueError("Select a wheelhouse directory or ZIP file.")
    destination = Path(destination)
    with zipfile.ZipFile(source) as archive:
        for member in archive.infolist():
            target = (destination / member.filename).resolve()
            if (
                not target.is_relative_to(destination.resolve())
                or "\\" in member.filename
                or (member.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Wheelhouse contains an unsafe archive path.")
        archive.extractall(destination)
    return destination


def installation_commands(
    product,
    directory,
    base_python,
    requirement,
    *,
    custom=False,
    offline=None,
    upgrade=False,
    release=None,
    interpreter=None,
):
    """Plan validated installation into a dedicated environment using its Python."""
    root = Path(directory).expanduser().absolute()
    python = python_executable(root)
    is_environment = (root / "pyvenv.cfg").is_file() or (root / "conda-meta").is_dir()
    if custom and (not is_environment or not python.is_file()):
        raise ValueError(
            "Choose an existing virtual or conda environment, not a system Python."
        )
    if not custom and root.exists() and not is_environment:
        raise ValueError(
            f"Refusing to reuse a directory that is not an environment: {root}"
        )
    probe_python = python if python.is_file() else Path(base_python).expanduser()
    if not probe_python.is_file():
        raise ValueError(
            "Select a compatible Python executable from the Create environments tab or Browse."
        )
    if offline and "git+" in requirement:
        raise ValueError("Offline installation supports releases, not Git branches.")
    release = release or ReleaseInfo("selected release", product.python, requirement)
    interpreter = validate_python(
        interpreter or inspect_python(probe_python), product, release
    )
    expected = Version(interpreter.version).release[:3]
    # Detect interpreter changes after preflight without requiring packaging in
    # the target environment. Full PEP 440 validation runs in the manager above.
    probe = (
        "import sys,struct; "
        f"assert sys.version_info[:3] == {expected!r}, "
        "'The Python interpreter changed after validation; retry installation'; "
        "assert struct.calcsize('P') == 8, 'A 64-bit Python is required'"
    )
    commands = [[str(probe_python), "-I", "-c", probe]]
    if not python.is_file():
        commands.append([str(probe_python), "-I", "-m", "venv", str(root)])
    commands.append(
        [
            str(python),
            "-I",
            "-c",
            "import importlib.util,runpy; "
            "runpy.run_module('ensurepip',run_name='__main__') "
            "if importlib.util.find_spec('pip') is None else None",
        ]
    )
    command = [str(python), "-I", "-m", "pip", "--disable-pip-version-check", "install"]
    if upgrade or requirement == product.package:
        command.append("--upgrade")
    if offline:
        command.extend(["--no-index", "--find-links", str(offline)])
    command.append(requirement)
    commands.append(command)
    commands.append([str(python), "-I", "-m", "pip", "check"])
    return commands


@dataclass(frozen=True)
class InstallationPlan:
    """Hold a resolved release and the commands validated for its interpreter."""

    release: ReleaseInfo
    interpreter: PythonInfo
    commands: list[list[str]]
    creating_environment: bool


def _installed_pythons():
    # Import lazily: discovery also uses this module's configuration path.
    from ansys.tools.installer.find_python import find_all_python, find_miniforge

    discovered = find_all_python()
    discovered.update(find_miniforge())
    entries = sorted(
        discovered.items(),
        key=lambda item: (str(item[1][0]).startswith("3.13"), str(item[1][0])),
        reverse=True,
    )
    return [str(python_executable(path)) for path, _metadata in entries]


def prepare_installation(
    product,
    directory,
    base_python,
    *,
    version="",
    source="release",
    branch="main",
    custom=False,
    wheelhouse=None,
    extract_to=None,
    upgrade=False,
):
    """Resolve the requested release and supported Python before mutating an environment."""
    release, offline = resolve_release(
        product,
        version=version,
        source=source,
        branch=branch,
        wheelhouse=wheelhouse,
        extract_to=extract_to,
    )
    root = Path(directory).expanduser().absolute()
    existing = python_executable(root)
    creating = not existing.is_file()
    if not creating:
        try:
            interpreter = validate_python(inspect_python(existing), product, release)
        except ValueError as error:
            raise ValueError(
                f"{error}\nThis existing environment was preserved. Create a supported "
                "environment in Create virtual environments and select it here."
            ) from error
    elif custom:
        raise ValueError(
            "Choose an existing virtual or conda environment, not a system Python."
        )
    else:
        try:
            interpreter = compatible_python(product, release, base_python)
        except ValueError:
            interpreter = compatible_python(
                product, release, base_python, _installed_pythons()
            )
    commands = installation_commands(
        product,
        root,
        interpreter.executable,
        release.requirement,
        custom=custom,
        offline=offline,
        upgrade=upgrade or (source == "release" and not version),
        release=release,
        interpreter=interpreter,
    )
    return InstallationPlan(release, interpreter, commands, creating)


def resolve_release(
    product,
    *,
    version="",
    source="release",
    branch="main",
    wheelhouse=None,
    extract_to=None,
):
    """Resolve the same exact release for selector checks and installation."""
    requirement = package_requirement(product, source, version, branch)
    offline = prepare_wheelhouse(wheelhouse, extract_to) if wheelhouse else None
    if offline:
        if source == "branch":
            raise ValueError(
                "Offline installation supports releases, not Git branches."
            )
        release = wheelhouse_release(product, offline, version)
    elif source == "branch":
        release = source_release(product, branch, requirement)
    else:
        release = published_release(product, version)
    return release, offline


def available_versions(product):
    """Fetch non-yanked stable versions with a bounded, verified HTTPS request."""
    response = requests.get(f"https://pypi.org/pypi/{product.package}/json", timeout=20)
    response.raise_for_status()
    return sorted(
        [
            version
            for version, files in response.json()["releases"].items()
            if files
            and any(not file.get("yanked") for file in files)
            and not Version(version).is_prerelease
        ],
        key=Version,
        reverse=True,
    )


def server_arguments(product, transport="stdio", port=8080, extra=()):
    """Build product-specific CLI arguments, keeping transport flags unambiguous."""
    if transport not in ("stdio", "http"):
        raise ValueError("Unknown MCP transport.")
    reserved = {"--transport", "--http-host", "--http-port"}
    if product.http_flags == ("--host", "--port"):
        reserved.update(product.http_flags)
    if any(argument.split("=", 1)[0] in reserved for argument in extra):
        raise ValueError(
            "Set HTTP/stdio transport and HTTP port in the connection controls."
        )
    if product.http_flags is None:
        if transport != "stdio":
            raise ValueError(f"{product.name} currently supports stdio only.")
        return list(extra)
    arguments = ["--transport", transport]
    if transport == "http":
        if not 1 <= port <= 65535:
            raise ValueError("HTTP port must be between 1 and 65535.")
        host_flag, port_flag = product.http_flags
        arguments.extend([host_flag, "127.0.0.1", port_flag, str(port)])
    return [*arguments, *extra]

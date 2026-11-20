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

"""Resolve exact MCP releases and validate their supported Python interpreters."""

from dataclasses import dataclass
from email.parser import Parser
import json
import os
from pathlib import Path
import subprocess
import zipfile

from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name, parse_wheel_filename
from packaging.version import Version
import requests
import tomlkit


@dataclass(frozen=True)
class ReleaseInfo:
    """Describe the exact package selected for an installation."""

    version: str
    requires_python: str
    requirement: str


@dataclass(frozen=True)
class PythonInfo:
    """Describe a selected interpreter without importing any third-party package."""

    executable: str
    version: str
    bits: int


def _requires_python(value, fallback):
    result = value or fallback
    SpecifierSet(result)
    return result


def published_release(product, version=""):
    """Resolve latest or a requested release from PyPI, without compatible fallback."""
    suffix = f"/{Version(version)}" if version else ""
    response = requests.get(
        f"https://pypi.org/pypi/{product.package}{suffix}/json", timeout=20
    )
    response.raise_for_status()
    data = response.json()
    info = data["info"]
    resolved = str(Version(info["version"]))
    if canonicalize_name(info["name"]) != canonicalize_name(product.package):
        raise ValueError("PyPI returned metadata for a different package.")
    if version and Version(resolved) != Version(version):
        raise ValueError("PyPI returned a different release from the selected version.")
    files = data.get("urls", [])
    if not files or all(file.get("yanked", False) for file in files):
        raise ValueError(
            f"{product.name} {resolved} has no non-yanked distribution files."
        )
    return ReleaseInfo(
        resolved,
        _requires_python(info.get("requires_python"), product.python),
        f"{product.package}=={resolved}",
    )


def source_release(product, branch, requirement):
    """Read the Python declaration from the selected official Git source."""
    response = requests.get(
        f"https://api.github.com/repos/ansys/{product.key}-mcp/contents/pyproject.toml",
        params={"ref": branch},
        headers={"Accept": "application/vnd.github.raw+json"},
        timeout=20,
    )
    response.raise_for_status()
    project = tomlkit.parse(response.text)["project"]
    if canonicalize_name(project["name"]) != canonicalize_name(product.package):
        raise ValueError("The Git source declares a different package name.")
    return ReleaseInfo(
        f"Git: {branch}",
        _requires_python(project.get("requires-python"), product.python),
        requirement,
    )


def wheelhouse_release(product, directory, version=""):
    """Resolve the newest stable local wheel, or the explicitly selected version."""
    candidates = []
    for path in Path(directory).glob("*.whl"):
        name, candidate, _build, _tags = parse_wheel_filename(path.name)
        if canonicalize_name(name) == canonicalize_name(product.package):
            if (version and candidate == Version(version)) or (
                not version and not candidate.is_prerelease
            ):
                candidates.append((candidate, path))
    if not candidates:
        raise ValueError(
            f"No wheel for {product.package}{'==' + version if version else ''} was found in the wheelhouse."
        )
    selected = max(candidate for candidate, _path in candidates)
    requirements = set()
    for candidate, path in candidates:
        if candidate != selected:
            continue
        with zipfile.ZipFile(path) as archive:
            metadata = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(metadata) != 1:
                raise ValueError(
                    f"Wheel has invalid distribution metadata: {path.name}"
                )
            message = Parser().parsestr(archive.read(metadata[0]).decode("utf-8"))
            if (
                canonicalize_name(message["Name"] or "")
                != canonicalize_name(product.package)
                or Version(message["Version"]) != selected
            ):
                raise ValueError(
                    f"Wheel metadata does not match its filename: {path.name}"
                )
            requirements.add(
                _requires_python(message.get("Requires-Python"), product.python)
            )
    # A release can contain platform wheels with different declarations. The
    # shared supported range is safe for every wheel the resolver might select.
    requires_python = str(SpecifierSet(",".join(sorted(requirements))))
    return ReleaseInfo(str(selected), requires_python, f"{product.package}=={selected}")


def inspect_python(executable):
    """Probe Python with a timeout and no inherited Python startup configuration."""
    path = Path(executable).expanduser().absolute()
    if not path.is_file():
        raise ValueError(f"Python executable not found: {path}")
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    command = [
        str(path),
        "-I",
        "-c",
        "import json,platform,struct; print(json.dumps({'version':platform.python_version(),'bits':struct.calcsize('P')*8}))",
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
        timeout=15,
        env=environment,
        **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}),
    )
    data = json.loads(result.stdout)
    return PythonInfo(str(path), str(Version(data["version"])), int(data["bits"]))


def validate_python(info, product, release):
    """Enforce both published release metadata and the documented product range."""
    required = SpecifierSet(release.requires_python) & SpecifierSet(product.python)
    if info.bits != 64 or Version(info.version) not in required:
        raise ValueError(
            f"{product.name} {release.version} requires 64-bit Python {required}; "
            f"the selected interpreter is Python {info.version} ({info.bits}-bit). "
            "Choose a supported Python in Create virtual environments or install one in Install Python."
        )
    return info


def compatible_python(product, release, preferred, candidates=()):
    """Keep a compatible chosen interpreter, otherwise choose an installed one."""
    errors = []
    for executable in dict.fromkeys([preferred, *candidates]):
        if not executable:
            continue
        try:
            return validate_python(inspect_python(executable), product, release)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append(str(error))
    raise ValueError(
        f"No installed 64-bit Python satisfies {product.name} {release.version} "
        f"({release.requires_python}; documented support {product.python}). "
        "Install a supported Python using Install Python, then retry."
        + (f"\n{errors[0]}" if errors else "")
    )

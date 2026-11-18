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

"""Read release requirements and inspect APM's discovered Python environments."""

from dataclasses import dataclass
from pathlib import Path
import tempfile

from ansys.tools.installer.mcp_backend import resolve_release
from ansys.tools.installer.mcp_releases import (
    PythonInfo,
    ReleaseInfo,
    inspect_python,
    validate_python,
)


@dataclass(frozen=True)
class Compatibility:
    """Hold a release and the supported/unsupported interpreter choices."""

    release: ReleaseInfo
    interpreters: dict[str, PythonInfo]
    errors: dict[str, str]
    probes: dict


def check_compatibility(
    product,
    paths,
    *,
    version="",
    source="release",
    branch="main",
    wheelhouse=None,
    probes=None,
):
    """Check selected release metadata and actual interpreters without mutations."""
    with tempfile.TemporaryDirectory(prefix="apm-mcp-check-") as temporary:
        release, _offline = resolve_release(
            product,
            version=version,
            source=source,
            branch=branch,
            wheelhouse=wheelhouse,
            extract_to=temporary,
        )
    supported, errors = {}, {}
    cache = dict(probes or {})
    for executable in dict.fromkeys(paths):
        if not executable:
            continue
        try:
            path = Path(executable)
            stamp = path.stat().st_mtime_ns
            previous = cache.get(executable)
            info = (
                previous[1]
                if previous and previous[0] == stamp
                else inspect_python(executable)
            )
            cache[executable] = (stamp, info)
            supported[executable] = validate_python(info, product, release)
        except Exception as error:
            errors[executable] = str(error)
    return Compatibility(release, supported, errors, cache)

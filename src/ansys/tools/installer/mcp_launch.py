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

"""Read launch options from the installed MCP's parser without starting a server."""

import json
import os
import subprocess

from ansys.tools.installer.mcp_backend import python_executable

# Intercept parsing before any launcher can create its server or connect a solver.
# Run in the target environment: APM never imports a solver package itself.
_INSPECT = r"""
import argparse, contextlib, importlib.metadata, io, json, sys
class Captured(BaseException): pass
def capture(parser, *args, **kwargs):
    options = []
    for action in parser._actions:
        flags = [f for f in action.option_strings if f.startswith('--')]
        if not flags or isinstance(action, (argparse._HelpAction, argparse._VersionAction)):
            continue
        if action.help == argparse.SUPPRESS:
            continue
        kind = 'flag' if action.nargs == 0 else 'value'
        options.append(dict(flags=flags, kind=kind, nargs=action.nargs,
            choices=list(action.choices) if action.choices is not None else None,
            type=getattr(action.type, '__name__', 'str'), help=action.help or '',
            default=action.default if isinstance(action.default, (str,int,float,bool,list,type(None))) else None))
    sys.__stdout__.write('APM_OPTIONS=' + json.dumps(options) + '\n')
    raise Captured()
argparse.ArgumentParser.parse_args = capture
argparse.ArgumentParser.parse_known_args = capture
package, command = sys.argv[1:3]
sys.argv = [command, '--help']
try:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        distribution = importlib.metadata.distribution(package)
        entry = next(e for e in distribution.entry_points if e.group == 'console_scripts' and e.name == command)
        entry.load()()
except Captured:
    pass
else:
    raise RuntimeError('The launcher did not expose an argparse parser.')
"""


def launch_options(environment, product):
    """Return parser metadata for this installed release, using a hidden subprocess."""
    if product.key == "pylumerical":
        return []  # Its FastMCP entry point does not parse command-line arguments.
    process = subprocess.run(
        [
            str(python_executable(environment)),
            "-I",
            "-c",
            _INSPECT,
            product.package,
            product.package,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=45,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    for line in process.stdout.splitlines():
        if line.startswith("APM_OPTIONS="):
            return json.loads(line.removeprefix("APM_OPTIONS="))
    raise ValueError(
        "This release's launch options could not be read. See its documentation."
    )


def option_arguments(options, values):
    """Validate selected values against the installed parser and serialize argv."""
    schema = {option["flags"][0]: option for option in options}
    arguments = []
    for flag, value in values.items():
        if flag not in schema:
            raise ValueError(f"{flag} is not supported by this installed MCP release.")
        option = schema[flag]
        if option["kind"] == "flag":
            if value is not True:
                raise ValueError(f"{flag} must be enabled or removed.")
            arguments.append(flag)
            continue
        values_list = value if isinstance(value, list) else [value]
        nargs = option["nargs"]
        if (
            nargs in (None, "?")
            and len(values_list) != 1
            or nargs == "+"
            and not values_list
            or type(nargs) is int
            and len(values_list) != nargs
        ):
            raise ValueError(f"Incorrect number of values for {flag}.")
        for entry in values_list:
            if not isinstance(entry, str) or not entry or "\0" in entry:
                raise ValueError(f"Enter a value for {flag}.")
            if option["choices"] is not None and entry not in map(
                str, option["choices"]
            ):
                raise ValueError(f"Unsupported value for {flag}.")
            if option["type"] in ("int", "validate_port", "_validate_port"):
                try:
                    int(entry)
                except ValueError as error:
                    raise ValueError(f"{flag} requires a whole number.") from error
        arguments.extend([flag, *values_list])
    return arguments

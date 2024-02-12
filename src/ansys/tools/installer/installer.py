# Copyright (C) 2023 - 2024 ANSYS, Inc. and/or its affiliates.
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

"""Installer module for Ansys Python Manager."""

import logging
import subprocess

LOG = logging.getLogger(__name__)


def run_ps(command, full_path_to_ps=False):
    """Run a powershell command as admin."""
    ps = (
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        if full_path_to_ps
        else "powershell.exe"
    )
    ps_command = [ps, command]

    LOG.debug("Running: %s", str(ps_command))
    proc = subprocess.run(
        ps_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=True,
    )

    # stderr goes through stdout too
    if proc.returncode:  # If return code != 0
        LOG.error("From powershell: %s", proc.stdout)
        if full_path_to_ps == False:
            return run_ps(command, full_path_to_ps=True)

    else:
        LOG.debug("From powershell: %s", proc.stdout)

    return proc.stdout, proc.returncode


def install_python(filename, wait=True):
    """Install "vanilla" python for a single user."""
    wait_str = " -Wait" if wait else ""
    command = f"(Start-Process '{filename}' -ArgumentList '/passive InstallAllUsers=0' {wait_str})"
    return run_ps(command)

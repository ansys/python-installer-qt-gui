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

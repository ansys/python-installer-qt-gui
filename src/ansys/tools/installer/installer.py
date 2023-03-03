"""Installer module for Ansys Python Manager."""
import logging
import subprocess

LOG = logging.getLogger(__name__)


def run_ps(command, wait=True):
    """Run a powershell command as admin."""
    ps_command = ["powershell.exe", command]
    LOG.debug("Running: %s", str(ps_command))
    proc = subprocess.Popen(
        ps_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
    )
    out, error = proc.communicate()

    LOG.debug("From powershell: %s", out)
    if error:
        LOG.error("From powershell: %s", error)

    return out, error


def install_python(filename, wait=True):
    """Install "vanilla" python for a single user."""
    wait_str = " -Wait" if wait else ""
    command = f'(Start-Process {filename} -ArgumentList "/passive InstallAllUsers=0" {wait_str})'
    return run_ps(command)

"""

"""
import logging
import subprocess

LOG = logging.getLogger(__name__)


def run_ps(command, wait=True):
    """Run a powershell command as admin."""
    ps_command = ["powershell.exe", "-command", command]
    if wait:
        ps_command.append("-Wait")
    LOG.debug("Running: %s", str(ps_command))
    proc = subprocess.Popen(
        ps_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    out, error = proc.communicate()

    LOG.debug("From powershell: %s", out)
    if error:
        LOG.error("From powershell: %s", error)

    return out, error


def install_python(filename):
    """Install "vanilla" python for a single user."""
    command = f'(Start-Process {filename} -ArgumentList "/passive InstallAllUsers=0")'
    return run_ps(command)

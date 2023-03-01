import logging
import os
import subprocess

try:
    import winreg
except ModuleNotFoundError as err:
    import platform

    if platform.system() == "Windows":
        raise err
    else:
        # This means that we are trying to build the docs,
        # or develop on Linux... but definitely not "use" it on
        # an OS different than Windows since it would crash. So,
        # just ignore it.
        pass

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


def find_miniforge():
    """Find all installations of miniforge."""
    forge = _find_miniforge(True)
    forge.update(_find_miniforge(False))
    return forge


def _find_miniforge(admin=False):
    if admin:
        root_key = winreg.HKEY_LOCAL_MACHINE
    else:
        root_key = winreg.HKEY_CURRENT_USER

    paths = {}
    key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
    with winreg.OpenKey(
        root_key,
        key,
        access=winreg.KEY_READ,
    ) as reg_key:
        info = winreg.QueryInfoKey(reg_key)
        for i in range(info[0]):
            subkey_name = winreg.EnumKey(reg_key, i)
            if "Miniforge" in subkey_name:
                with winreg.OpenKey(
                    root_key,
                    key + "\\" + subkey_name,
                    access=winreg.KEY_READ,
                ) as sub_key:
                    ver = winreg.QueryValueEx(sub_key, "DisplayVersion")[0]
                    uninstall_exe = winreg.QueryValueEx(sub_key, "UninstallString")[
                        0
                    ].replace('"', "")
                    miniforge_path = os.path.dirname(uninstall_exe)
                    paths[miniforge_path] = (ver, admin)
    return paths


def find_installed_python(version, admin=False):
    """Check the registry for any installed instances of Python."""

    if admin:
        key = winreg.HKEY_LOCAL_MACHINE
    else:
        key = winreg.HKEY_CURRENT_USER

    install_path = None
    try:
        with winreg.OpenKey(
            key,
            f"SOFTWARE\\Python\\PythonCore\\{version}\\InstallPath",
            access=winreg.KEY_READ,
        ) as reg_key:
            info = winreg.QueryInfoKey(reg_key)
            for i in range(info[1]):
                name, value, _ = winreg.EnumValue(reg_key, i)
                if name == "ExecutablePath":
                    if os.path.isfile(value) and value.endswith("python.exe"):
                        install_path = os.path.dirname(value)

    except FileNotFoundError:
        pass

    return install_path


def find_all_python():
    """Find any installed instances of python."""
    installed = [{}, {}]
    for admin in [True, False]:
        for version in range(7, 13):
            path = find_installed_python(f"3.{version}", admin)
            if path is not None:
                # quickly check the patch version of python
                command = f'{os.path.join(path, "python.exe")} --version'
                ps_command = ["powershell.exe", "-command", command]
                LOG.debug("Running: %s", str(ps_command))
                proc = subprocess.Popen(
                    ps_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                out, error = proc.communicate()
                nice_version = out.decode().strip()
                if "Python" in nice_version:
                    nice_version = nice_version.replace("Python", "").strip()
                    LOG.debug("Found %s at %s", nice_version, path)
                    installed[admin][nice_version] = path

    return installed

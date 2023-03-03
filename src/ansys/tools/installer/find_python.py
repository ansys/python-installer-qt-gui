"""Search for Python or miniforge installations within the Windows registry."""
import logging
import os

try:
    import winreg
except ModuleNotFoundError as err:
    import platform

    if platform.system() == "Windows":
        raise err
    else:
        # This means that we are trying to build the docs,
        # or develop on Linux... but definitely do not "use" it on
        # an OS different than Windows since it would crash. So,
        # just ignore it.
        pass

LOG = logging.getLogger(__name__)
LOG.setLevel("DEBUG")


def find_miniforge():
    """Find all installations of miniforge within the Windows registry.

    Returns
    -------
    dict
        Dictionary containing a key for each path and a ``tuple``
        containing ``(version_str, is_admin)``.

    """
    paths = _find_miniforge(True)
    paths.update(_find_miniforge(False))
    return paths


def _find_miniforge(admin=False):
    """Search for any miniforge installations in the registry."""
    if admin:
        root_key = winreg.HKEY_LOCAL_MACHINE
    else:
        root_key = winreg.HKEY_CURRENT_USER

    paths = {}
    key = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
    try:
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
    except FileNotFoundError:
        pass

    return paths


def _find_installed_python(admin=False):
    """Check the registry for any installed instances of Python."""
    if admin:
        root_key = winreg.HKEY_LOCAL_MACHINE
    else:
        root_key = winreg.HKEY_CURRENT_USER

    install_path = None
    paths = {}
    try:
        base_key = f"SOFTWARE\\Python\\PythonCore"
        with winreg.OpenKey(
            root_key,
            base_key,
            access=winreg.KEY_READ,
        ) as reg_key:
            info = winreg.QueryInfoKey(reg_key)
            for i in range(info[0]):
                name = winreg.EnumKey(reg_key, i)
                ver, path = get_python_info(f"{base_key}\\{name}", root_key)
                if ver is not None and path is not None:
                    paths[path] = (ver, admin)

    except FileNotFoundError:
        pass

    return paths


def get_python_info(key, root_key):
    """For a given key, read the install path and python version."""
    with winreg.OpenKey(root_key, key, access=winreg.KEY_READ) as reg_key:
        try:
            ver = winreg.QueryValueEx(reg_key, "Version")[0]
        except FileNotFoundError:
            ver = None

        try:
            with winreg.OpenKey(
                root_key, f"{key}\\InstallPath", access=winreg.KEY_READ
            ) as path_key:
                path = winreg.QueryValueEx(path_key, None)[0]
        except FileNotFoundError:
            path = None

    return ver, path


def find_all_python():
    """Find any installed instances of python.

    Returns
    -------
    dict
        Dictionary containing a key for each path and a ``tuple``
        containing ``(version_str, is_admin)``.

    """
    paths = _find_installed_python(True)
    paths.update(_find_installed_python(False))
    return paths

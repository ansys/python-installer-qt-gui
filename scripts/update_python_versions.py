"""Script that updates the Python versions used in the project."""

import os
import re

from packaging.version import Version, parse
import requests


def is_version_string(s: str) -> bool:
    """Check if the string is in accepted version format.

    Parameters
    ----------
    s : str
        String to check.

    Returns
    -------
    bool
        True if the string is in the accepted version format, False otherwise.
    """
    pattern = r"^\d+\.\d+\.\d+$"
    return bool(re.match(pattern, s))


def get_latest_github_release(user, repo) -> dict:
    """Get the latest release of a GitHub repository.

    Parameters
    ----------
    user : str
        GitHub username.
    repo : str
        Repository name.

    Returns
    -------
    dict
        JSON response of the latest release.
    """
    url = f"https://api.github.com/repos/{user}/{repo}/releases/latest"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get releases: {response.content}")
        return None


def get_minor_version_sublist_with_greater_patch(list: list[str], current_version: str):
    """Get the sublist of versions with greater patch than the current version."""
    major, minor, patch = current_version.split(".")
    major, minor, patch = int(major), int(minor), int(patch)
    sublist = [version for version in list if version.startswith(f"{major}.{minor}.")]
    sublist = [version for version in sublist if int(version.split(".")[2]) > patch]
    sublist = sorted(sublist, key=Version, reverse=True)

    return sublist


# Get path to the root of the project
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Path to the constants file
CONSTANTS_FILE = os.path.join(
    ROOT_DIR, "src", "ansys", "tools", "installer", "constants.py"
)

# Parse the constants file to find the current Python versions
# used in the project. The versions are stored in a tuple
with open(CONSTANTS_FILE, "r") as f:
    lines = f.readlines()

# Import the following constants inside the constants file
#
# Example:
#
# VANILLA_PYTHON_VERSIONS = {
#     "Python 3.8": "3.8.10",
#     "Python 3.9": "3.9.13",
#     "Python 3.10": "3.10.11",
#     "Python 3.11": "3.11.6",
#     "Python 3.12": "3.12.0",
# }
#
# CONDA_PYTHON_VERSION = "23.1.0-4"
#

vanilla_python_versions: dict[str, str] = {}
conda_python_version: str = ""

for line in lines:
    if "VANILLA_PYTHON_VERSIONS" in line:
        # Store the index of the line where the dictionary starts
        start_index = lines.index(line)
        break

# Get the dictionary that contains the Python versions
for line in lines[start_index:]:
    if "}" in line:
        # Store the index of the line where the dictionary ends
        end_index = lines.index(line, start_index)
        break

# Parse the dictionary to get the Python versions
for line in lines[start_index : end_index + 1]:
    if "Python" in line:
        # Extract the Python version and the version number
        python_version = line.split(":")[0].strip().replace('"', "")
        version_number = line.split(":")[1].strip().replace('"', "").replace(",", "")

        # Store the Python version and the version number
        vanilla_python_versions[python_version] = version_number

# Get the Conda Python version
for line in lines:
    if "CONDA_PYTHON_VERSION" in line:
        conda_python_version = line.split("=")[1].strip().replace('"', "")

# LOG - Print the current Python versions
print("Current Vanilla Python versions:")
for version in vanilla_python_versions.values():
    print(f">>> '{version}'")

print("Current Conda Python version")
print(f">>> '{conda_python_version}'")

# --------------------------------------------------------------------------------------------

print("--- \nUpdating Python versions...\n")

# Check remote Python versions available
PYTHON_FTP = "https://www.python.org/ftp/python"

# List all folders in the Python FTP
response = requests.get(PYTHON_FTP)
text = response.text.split("\n")
ftp_versions = []
for line in text:
    tmp = line.strip('<a href="').split('/">')[0]
    # Check if the folder is a Python version
    if is_version_string(tmp):
        ftp_versions.append(tmp)

# For each minor version, get the patch versions available
# greter than the current patch version
for python_version_key, python_version_value in vanilla_python_versions.items():
    # Get the minor version of the current Python version
    minor_version = ".".join(python_version_value.split(".")[:2])

    # Get the patch versions available
    patch_versions = get_minor_version_sublist_with_greater_patch(
        ftp_versions, python_version_value
    )

    # Check if the patch versions contain the executable
    new_patch_version = None
    for patch_version in patch_versions:
        # Check if the executable exists
        response_1 = requests.get(
            f"{PYTHON_FTP}/{patch_version}/Python-{patch_version}.tar.xz"
        )
        response_2 = requests.get(
            f"{PYTHON_FTP}/{patch_version}/python-{patch_version}-amd64.exe"
        )
        if response_1.status_code == 200 and response_2.status_code == 200:
            print(f"Python {patch_version} is available for download")
            new_patch_version = patch_version
            break

    # Update the Python version
    if new_patch_version:
        vanilla_python_versions[python_version_key] = new_patch_version
    else:
        print(f"Python {python_version_value} is already the latest version available")

# Get the latest Conda Python version
latest_conda_release = get_latest_github_release("conda-forge", "miniforge")

# Verify that the assets are available
assets = latest_conda_release["assets"]
new_conda_version = None
count = 0
for asset in assets:
    if f"Miniforge3-{latest_conda_release['name']}-Linux-x86_64.sh" in asset["name"]:
        count += 1
    if f"Miniforge3-{latest_conda_release['name']}-Windows-x86_64.exe" in asset["name"]:
        count += 1
    if count == 2:
        new_conda_version = latest_conda_release["name"]
        break

# Update the Conda Python version
if new_conda_version:
    conda_python_version = new_conda_version
    print(f"Conda Python version updated to {conda_python_version}")
else:
    print(f"Conda Python version is already the latest version available")

print("\nPython versions updated successfully\n ---")

# --------------------------------------------------------------------------------------------

# LOG - Print the new Python versions
print("New Vanilla Python versions:")
for version in vanilla_python_versions.values():
    print(f">>> '{version}'")

print("New Conda Python version:")
print(f">>> '{conda_python_version}'")

# Update the constants file with the new Python versions
# Write the new Python versions to the constants file
with open(CONSTANTS_FILE, "w") as f:
    for line in lines[:start_index]:
        f.write(line)

    f.write("VANILLA_PYTHON_VERSIONS = {\n")
    for python_version, version_number in vanilla_python_versions.items():
        f.write(f'    "{python_version}": "{version_number}",\n')
    f.write("}\n\n")

    f.write(f'CONDA_PYTHON_VERSION = "{conda_python_version}"\n')


# Path for ci_cd.yaml
YAML_FILE = os.path.join(ROOT_DIR, ".github", "workflows", "ci_cd.yml")

# Read the file
with open(YAML_FILE, "r") as f:
    yaml_contents = f.readlines()
    print(yaml_contents)

# Get pattern to replace
py_version = parse(list(vanilla_python_versions.values())[-2])
py_version_search = f"{str(py_version.major)}.{str(py_version.minor)}"
search_str = re.compile(py_version_search + "\.[\d]{1,}")

# Replace the version
for n, yaml_line in enumerate(yaml_contents):
    if "PRECOMPILE_PYTHON_VERSION:" in yaml_line:
        yaml_contents[n] = search_str.sub(py_version.base_version, yaml_line)

# Rewrite the yaml file
with open(YAML_FILE, "w") as yaml:
    yaml.writelines(yaml_contents)

with open(YAML_FILE, "r") as f:
    yaml_contents = f.readlines()
    print(yaml_contents)

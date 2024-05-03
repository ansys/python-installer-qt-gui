"""Script that updates the Python versions used in the project."""

import os
import re
import subprocess

from packaging.version import parse

print(subprocess.check_output(["ls", "-alRtr"]).decode("utf-8"))

print(subprocess.check_output(["pwd"]).decode("utf-8"))

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#
vanilla_python_versions = ("3.9.13",)


# Path for ci_cd.yaml
YAML_FILE = os.path.join(ROOT_DIR, ".github", "workflows", "ci_cd.yaml")

# Read the file
with open(YAML_FILE, "r") as f:
    yaml_contents = f.readlines()

# Get pattern to replace
py_version = parse(vanilla_python_versions)
py_version_search = f"{str(py_version.major)}.{str(py_version.minor)}"
search_str = re.compile(py_version_search + "\.[\d]{1,}")

# Replace the version
for n, yaml_line in enumerate(yaml_contents):
    if "PRECOMPILE_PYTHON_VERSION:" in yaml_line:
        yaml_contents[n] = search_str.sub(py_version.base_version, yaml_line)

# Rewrite the yaml file
with open(YAML_FILE, "w") as yaml:
    yaml.writelines(yaml_contents)

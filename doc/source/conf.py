"""Sphinx documentation configuration file."""
from datetime import datetime
import os
import shutil

from ansys_sphinx_theme import get_version_match
from ansys_sphinx_theme import pyansys_logo_black as logo

from ansys.tools.installer import __version__

# Project information
project = "python-installer-qt-gui"
copyright = f"(c) {datetime.now().year} ANSYS, Inc. All rights reserved"
author = "ANSYS, Inc."
release = version = __version__
cname = os.getenv("DOCUMENTATION_CNAME", default="nocname.com")
switcher_version = get_version_match(__version__)

# Select desired logo, theme, and declare the html title
html_logo = logo
html_theme = "ansys_sphinx_theme"
html_short_title = html_title = "Python GUI Installer"

# specify the location of your github repo
html_context = {
    "github_user": "pyansys",
    "github_repo": "python-installer-qt-gui",
    "github_version": "main",
    "doc_path": "doc/source",
}
html_theme_options = {
    "switcher": {
        "json_url": f"https://{cname}/versions.json",
        "version_match": switcher_version,
    },
    "github_url": "https://github.com/pyansys/python-installer-qt-gui",
    "show_prev_next": False,
    "show_breadcrumbs": True,
    "additional_breadcrumbs": [
        ("PyAnsys", "https://docs.pyansys.com/"),
    ],
    "github_url": "https://github.com/pyansys/python-installer-qt-gui",
}

# Sphinx extensions
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/dev", None),
    # kept here as an example
    # "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    # "numpy": ("https://numpy.org/devdocs", None),
    # "matplotlib": ("https://matplotlib.org/stable", None),
    # "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    # "pyvista": ("https://docs.pyvista.org/", None),
    # "grpc": ("https://grpc.github.io/grpc/python/", None),
}

# static path
html_static_path = ["_static", "images"]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# Copying README images
shutil.copytree("../../images", "images", dirs_exist_ok=True)

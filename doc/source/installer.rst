Install Python on Windows
#########################

This document shows users how to install Python on a Windows machine.

In order to do so, just follow the upcoming steps:

#. Download the necessary installer from the `latest available release <https://github.com/pyansys/python-installer-gui/releases/latest>`_.
   The file should be named ``python-installer-gui-v*.zip``

#. Unzip the file and extract the ``Ansys Python Installer Setup`` executable.

#. Select your desired Python install, version and extra packages.

#. And follow the install process. Finally, test out your new Python install by running the following:

.. code-block:: bash

    python -c "print('Hello World!')"

Configurable options for the installer
--------------------------------------

Two Python options for installation are available:

* ``Standard``: this mode installs the standard Python version from `python.org <https://www.python.org/>`_
* ``miniforge``: this mode installs the Python version from `miniforge <https://github.com/conda-forge/miniforge>`_.
  This install is characterized for being a modified ``conda`` install in which you have access to the ``conda``
  package manager through the ``conda-forge`` channel.

Regarding the available Python versions, the following are available:

* Python 3.7
* Python 3.8
* Python 3.9
* Python 3.10
* Python 3.11

Finally, the following extra packages are available for installing:

* ``Defaults``: by selecting this option, your clean Python install also provides you with
  the latest compatible versions of your Python version for ``numpy``, ``scipy``,
  ``pandas``, ``matplotlib`` and  ``scikit-learn``.
* ``PyAnsys``: by selecting this option, users have access to the latest PyAnsys metapackage installation.
  This metapackage provides you with access to the latest public PyAnsys libraries in their compatible
  version with the latest Ansys products.
* ``Jupyterlab``: by selecting this option, users have access to JupyterLab capabilities (that is, deploying a
  JupyterLab server locally, running Jupyter notebooks etc.).
* ``Spyder``: by selecting this option, users are granted with a Spyder IDE install.

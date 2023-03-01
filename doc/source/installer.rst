Usage instructions
##################

Installing the ``Ansys Python Manager``
=======================================

First step is installing the ``Ansys Python Manager``. In order to do so, follow the next steps.

#. Download the necessary installer from the `latest available release <https://github.com/pyansys/python-installer-qt-gui/releases/latest>`_.
   The file should be named ``python-installer-gui.zip``

#. Unzip the file and extract the ``Ansys Python Manager Setup`` executable.

#. Execute the installer.

#. Search for the ``Ansys Python Manager`` and run it.

The ``Ansys Python Manager`` window should appear at this stage.

Installing Python on Windows
============================

Now, instructions on how to install Python from the ``Ansys Python Manager`` are provided.

In order to do so, just follow the upcoming steps:

#. Search for the ``Ansys Python Manager`` and run it.

#. Go to the ``Install Python`` tab, and select your desired Python install, version and extra packages.

#. And follow the install process.


Configurable options for the installer
--------------------------------------

Two Python options for installation are available:

* ``Standard``: this mode installs the standard Python version from `python.org <https://www.python.org/>`_
* ``Conda (miniforge)``: this mode installs the Python version from `miniforge <https://github.com/conda-forge/miniforge>`_.
  This install is characterized for being a modified ``conda`` install in which you have access to the ``conda``
  package manager through the ``conda-forge`` channel.

Regarding the available Python versions, users can select among the following ones:

* Python 3.7
* Python 3.8
* Python 3.9
* Python 3.10
* Python 3.11

.. warning::

  In the case of having selected ``Conda (miniforge)``, only Python 3.10 is available.

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

.. warning::

  Currently we are experiencing problems when installing them by default.
  For the time being, it may be necessary to install them by hand. If you are using
  the ``Standard`` install then you should call ``pip install ...`` from a cmd. If you
  are using ``Conda (miniforge)``, then it should be ``conda install ...``.

Managing Python environments
============================

Through the ``Ansys Python Manager``, users can also have access to their different Python
installations. Let's have a look at how to access it.

#. Search for the ``Ansys Python Manager`` and run it.

#. Access the ``Manage Python Environments`` tab.

#. Select your desired ``Python`` environment and start one of the listed options.

Several options are provided to users:

* ``Launch Console``: this option will start a console window with Python started.
* ``Launch JupyterLab``: this option will start a ``JupyterLab`` session. If ``JupyterLab`` is
  not installed, then the ``Ansys Python Manager`` installs it for you.
* ``Launch Jupyter Notebook``: this option will start a ``Jupyter Notebook`` session. If
  ``Jupyter Notebook`` is not installed, then the ``Ansys Python Manager`` installs it for you.
* ``Launch Spyder``: this option will start a Spyder IDE session. If Spyder is not installed,
  then the ``Ansys Python Manager`` installs it for you.
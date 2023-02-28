Ansys Python Installer (QT)
===========================

This is a simple cross-platform [QT](https://www.qt.io/) application
you can use to install Python and (optional) PyAnsys packages.


Installation
~~~~~~~~~~~~
Visit the `Releases
<https://github.com/pyansys/python-installer-qt-gui/releases>`_ page and pull
down the latest installer. This is a simple application you can use to install
Python and manage your Python enviornment.


For developers
^^^^^^^^^^^^^^

Installing Pytools installer in developer mode allows
you to modify the source and enhance it.

Before contributing to the project, please refer to the `PyAnsys Developer's guide`_. You will 
need to follow these steps:

#. Start by cloning this repository:

.. code:: bash

   git clone https://github.com/pyansys/pytools-installer

#. Create a fresh-clean Python environment and activate it. Refer to the
   official `venv`_ documentation if you require further information:

.. code:: bash

   # Create a virtual environment
   python -m venv .venv

   # Activate it in a POSIX system
   source .venv/bin/activate

   # Activate it in Windows CMD environment
   .venv\Scripts\activate.bat

   # Activate it in Windows Powershell
   .venv\Scripts\Activate.ps1

#. Make sure you have the latest version of `pip`_:

.. code:: bash

   python -m pip install -U pip

#. Install the project in editable mode:

.. code:: bash
    
   python -m pip install --editable ansys-tools-installer

#. Install additional requirements (if needed):

.. code:: bash

   python -m pip install -r requirements/requirements_build.txt
   python -m pip install -r requirements/requirements_doc.txt
   python -m pip install -r requirements/requirements_tests.txt

#. Finally, verify your development installation by running:

.. code:: bash
        
   python -m pip install -r requirements/requirements_tests.txt
   pytest tests -v


Style and Testing
-----------------



Documentation
-------------

For building documentation, you can either run the usual rules provided in the
`Sphinx`_ Makefile, such us:

.. code:: bash

    python -m pip install -r requirements/requirements_doc.txt
    make -C doc/ html

    # subsequently open the documentation with (under Linux):
    your_browser_name doc/html/index.html

Distributing
------------

If you would like to create either source or wheel files, start by installing
the building requirements:

.. code:: bash

    python -m pip install -r requirements/requirements_build.txt

Then, you can execute:

.. code:: bash

    python -m build
    python -m twine check dist/*


.. LINKS AND REFERENCES
.. _black: https://github.com/psf/black
.. _flake8: https://flake8.pycqa.org/en/latest/
.. _isort: https://github.com/PyCQA/isort
.. _PyAnsys Developer's guide: https://dev.docs.pyansys.com/
.. _pre-commit: https://pre-commit.com/
.. _pytest: https://docs.pytest.org/en/stable/
.. _Sphinx: https://www.sphinx-doc.org/en/master/
.. _pip: https://pypi.org/project/pip/
.. _tox: https://tox.wiki/
.. _venv: https://docs.python.org/3/library/venv.html

"""
Ansys Python Manager
"""

__version__ = "0.0.dev0"

import logging
import os
import warnings
from appdirs import user_cache_dir
from ansys.tools.installer.main import AnsysPythonInstaller, open_gui


CACHE_DIR = user_cache_dir('ansys_python_installer')

if not os.path.isdir(CACHE_DIR):
    try:
        os.makedirs(CACHE_DIR)
    except:
        import tempdir

        warnings.warn(f'Unable create cache at {CACHE_DIR}. Using temporary directory')
        CACHE_DIR = tempdir.gettempdir()

ENABLE_LOGGING = True
if ENABLE_LOGGING:
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create a console handler that writes to stdout
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)

    # Add the console handler to the logger
    logger.addHandler(console_handler)

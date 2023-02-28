"""pyinstaller app generation"""
import glob
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# path where this file is located
try:
    THIS_PATH = os.path.dirname(__file__)
except NameError:
    THIS_PATH = os.getcwd()

OUT_PATH = 'ansys_python_manager'
APP_NAME = 'Ansys Python Manager'
ICON_FILE = os.path.join(
    THIS_PATH, 'src','ansys','tools','installer', 'assets', 'pyansys_icon.ico'
)

# consider testing paths
main_py = os.path.join(THIS_PATH, 'src/ansys/tools/installer/__main__.py')

if not os.path.isfile(main_py):
    raise FileNotFoundError(f'Unable to locate main entrypoint at {main_py}')

a = Analysis([main_py],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

# a.datas += [('.ico', icon_file, 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name=APP_NAME,
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=True,
          icon=ICON_FILE)

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name=OUT_PATH)

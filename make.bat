@ECHO OFF

pushd %~dp0

REM Simple make.bat to simplify repetitive build env management tasks under Windows

if "%1" == "install" goto install
if "%1" == "build" goto build
if "%1" == "clean" goto clean
if "%1" == "fresh-build" goto fresh-build

:install
Echo Installing...
pip install -e .[freeze]
pytest -v tests
Echo Installation complete.
goto end

:build
Echo Freezing using pyinstaller
pyinstaller frozen.spec
goto end

:clean
Echo Cleaning up build files...
rmdir /s /q build > /NUL 2>&1
rmdir /s /q dist > /NUL 2>&1
goto end

:fresh-build
Echo Cleaning up build files...
rmdir /s /q build > /NUL 2>&1
rmdir /s /q dist > /NUL 2>&1
Echo Freezing using pyinstaller
pyinstaller frozen.spec
goto end

:end
popd

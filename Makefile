# Simple makefile to simplify repetitive build env management tasks under posix

install:
	@echo "Installing..."
	pip install -e .[freeze]
	pytest -v --doctest-modules pyvista
	@echo "Installation complete."

build:
	@echo "Freezing using pyinstaller"
	pyinstaller frozen.spec

# Simple makefile to simplify repetitive build env management tasks under posix
.PHONY: install build clean fresh-build

install:
	@echo "Installing..."
	pip install -e .[freeze]
	pytest -v tests
	@echo "Installation complete."

build:
	@echo "Freezing using pyinstaller"
	pyinstaller frozen.spec

clean:
	@echo "Cleaning up build files..."
	rm -rf build dist

fresh-build: clean build

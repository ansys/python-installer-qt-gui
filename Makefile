# Simple makefile to simplify repetitive build env management tasks under posix
.PHONY: install tests doc build clean fresh-build

install:
	@echo "Installing..."
	pip install -e .[freeze]
	@echo "Installation complete."

tests:
	@echo "Installing test dependencies..."
	pip install -e .[tests]
	@echo "Running tests..."
	pytest
	@echo "Tests complete."

doc:
	@echo "Installing documentation dependencies..."
	pip install -e .[doc]
	@echo "Building documentation..."
	cd doc && make clean && make html && cd ..
	@echo "Documentation complete."

build:
	@echo "Freezing using pyinstaller"
	pyinstaller frozen.spec

clean:
	@echo "Cleaning up build files..."
	rm -rf build dist

fresh-build: clean build

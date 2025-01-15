# Simple makefile to simplify repetitive build env management tasks under posix
.PHONY: install tests doc build clean fresh-build

install:
	@echo "Installing uv..."
	pip install uv
	@echo "Installing..."
	uv pip install -e .[freeze]
	@echo "Installation complete."

tests:
	@echo "Installing uv..."
	pip install uv
	@echo "Installing test dependencies..."
	uv pip install -e .[tests]
	@echo "Running tests..."
	uv run pytest
	@echo "Tests complete."

doc:
	@echo "Installing uv..."
	pip install uv
	@echo "Installing documentation dependencies..."
	uv pip install -e .[doc]
	@echo "Building documentation..."
	cd doc && make clean && make html && cd ..
	@echo "Documentation complete."

build:
	@echo "Installing uv..."
	pip install uv
	@echo "Freezing using pyinstaller"
	uv run pyinstaller frozen.spec

clean:
	@echo "Installing uv..."
    pip install uv
	@echo "Cleaning up build files..."
	rm -rf build dist

fresh-build: clean build

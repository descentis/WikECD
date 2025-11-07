# =========================================
# WikECD Makefile – Simplify Dev Operations
# =========================================

PYTHON := python3
PACKAGE := WikECD
DIST_DIR := dist

# --- Installation and Environment ---
install:
	$(PYTHON) -m pip install -U pip build twine pytest
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m pip install -r requirements.txt

# --- Testing ---
test:
	pytest -v --maxfail=1 --disable-warnings

# --- Build & Clean ---
build:
	rm -rf $(DIST_DIR) build *.egg-info
	$(PYTHON) -m build

clean:
	rm -rf $(DIST_DIR) build *.egg-info .pytest_cache __pycache__ **/__pycache__

# --- Publishing ---
publish-test:
	twine upload -r testpypi $(DIST_DIR)/*

publish:
	twine upload -r pypi $(DIST_DIR)/*

# --- Linting & Formatting ---
lint:
	flake8 $(PACKAGE) --ignore=E203,W503

format:
	black $(PACKAGE)

# --- Docs (optional future section) ---
docs:
	@echo "TODO: generate docs using Sphinx or MkDocs"

# --- Convenience Commands ---
run:
	wikecd --help

info:
	@echo "Python: $$(which $(PYTHON))"
	@echo "Pip: $$(which pip)"
	@echo "Virtualenv: $$(which activate)"
	@echo "Package: $(PACKAGE)"

# --- Git Tagging & Versioning ---
tag:
	@if [ -z "$(v)" ]; then \
		echo "Usage: make tag v=0.1.2"; \
		exit 1; \
	fi
	git add .
	git commit -m "🔖 Release v$(v)"
	git tag -a "v$(v)" -m "Version $(v)"
	git push origin main --tags
	@echo "Tagged and pushed version $(v)"


.PHONY: compile install-dev test check clean

PYTHON ?= python3
VENV ?= .venv
export PYTHONPATH := src:.

compile:
	$(PYTHON) -m compileall -q src tests notebooks scripts

venv:
	$(PYTHON) -m venv $(VENV)

install-dev: venv
	$(VENV)/bin/python -m pip install -U pip
	$(VENV)/bin/python -m pip install -r requirements-dev.txt

test:
	$(VENV)/bin/python -m pytest

check: compile test

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +

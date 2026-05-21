.PHONY: compile test check smoke-direct-offline smoke-rss smoke-direct-real clean

PYTHON ?= python3
export PYTHONPATH := src:.

compile:
	$(PYTHON) -m compileall -q src tests notebooks scripts

test:
	$(PYTHON) scripts/run_unit_tests.py

test-pytest:
	$(PYTHON) -m pytest -q

smoke-direct-offline:
	$(PYTHON) scripts/smoke_direct_offline.py

smoke-rss:
	$(PYTHON) scripts/smoke_rss.py

smoke-direct-real:
	$(PYTHON) scripts/smoke_direct_real.py

check: compile smoke-direct-offline

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +

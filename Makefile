PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest

.PHONY: setup dev test benchmark

setup:
	$(PIP) install -r backend/requirements.txt

dev:
	PYTHONPATH=backend uvicorn hash_market.api:app --reload

test:
	PYTHONPATH=backend $(PYTEST) -q

benchmark:
	PYTHONPATH=backend $(PYTHON) -m hash_market.benchmark.runner

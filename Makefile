PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
PYTEST ?= $(PYTHON) -m pytest

.PHONY: setup dev test benchmark frontend-setup frontend-dev frontend-check

setup:
	$(PIP) install -r backend/requirements-dev.txt

dev:
	PYTHONPATH=backend uvicorn hash_market.api:app --reload

test:
	PYTHONPATH=backend $(PYTEST) -q

benchmark:
	PYTHONPATH=backend $(PYTHON) -m hash_market.benchmark.runner

frontend-setup:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-check:
	cd frontend && npm run lint && npm run build

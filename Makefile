.PHONY: install test run once heartbeat watchdog lint docker

VENV ?= .venv
PY ?= $(VENV)/bin/python

install:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -U pip
	$(VENV)/bin/pip install -e ".[dev]"

test:
	$(PY) -m pytest -q

run:
	$(PY) -m autoapply run

once:
	$(PY) -m autoapply once --dry-run

heartbeat:
	$(PY) -m autoapply heartbeat

watchdog:
	$(PY) -m autoapply watchdog

docker:
	docker compose up --build -d

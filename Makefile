PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
NPM ?= npm

.PHONY: install-backend install-frontend test build-frontend smoke lint compose-config

install-backend:
	$(PIP) install -e ./vendor/bilibili-api
	$(PIP) install -e './backend[dev]'

install-frontend:
	cd frontend && $(NPM) install

test:
	cd backend && ../.venv/bin/python -m pytest -q

build-frontend:
	cd frontend && $(NPM) run build

smoke:
	cd backend && APP_ENV=test DATABASE_URL=sqlite+pysqlite:///./make_smoke.db ../.venv/bin/python scripts/smoke.py

compose-config:
	docker compose config

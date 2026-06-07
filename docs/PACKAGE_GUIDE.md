# Package Guide

## Overview

This package contains the refactored Bilibili comment monitoring platform.
It is intended for source delivery, local development, and Docker Compose deployment.

Included areas:

- `backend/`: FastAPI backend, tests, worker tasks, schemas, services
- `frontend/`: React frontend source and production build output
- `deploy/`: Grafana, Prometheus, Loki provisioning
- `vendor/bilibili-api/`: vendored Bilibili API dependency
- `docs/DOUYIN.md`: Douyin module notes and authorization constraints
- AI reply integration via OpenAI Python SDK and configurable `base_url`
- `docker-compose.yml`: single-machine deployment entrypoint
- `.env.example`: environment variable template
- `README.md`: project overview and quick start
- `docs/`: delivery and testing documentation

Excluded from the packaged archive:

- `.venv/`
- `frontend/node_modules/`
- local sqlite databases under `backend/*.db`
- runtime QR images, tokens, and temporary files
- `.env`
- cache directories such as `.pytest_cache/`

## Recommended Startup Paths

### Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

### Local Development

Backend:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e ./vendor/bilibili-api
pip install -e './backend[dev]'
cd backend
APP_ENV=test DATABASE_URL=sqlite+pysqlite:///./local-start.db ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## Default Bootstrap Account

- Email: `owner@example.com`
- Password: `ChangeMe123!`

Change these values before production deployment.

## Notes

- The project vendors `Nemo2011/bilibili-api` locally instead of pulling from Git at install time.
- Real Bilibili QR login was validated locally before packaging.
- Worker and Beat processes are part of the project, but local app startup can be tested without them.

# Testing

## Automated Verification

The project was verified locally before packaging with:

```bash
cd backend && ../.venv/bin/python -m pytest -q
cd frontend && npm run build
```

Latest local results at packaging time:

- Backend: `29 passed`
- Frontend production build: passed

Covered areas include:

- authentication and refresh tokens
- tenant and member management
- webhook configuration
- target import preview and selective import
- reply draft creation and reply send flow
- analytics and system metrics
- comment event creation and update tracking
- audit logging for handling, drafts, and reply outcomes
- Douyin app/account/target creation plus mocked comment polling and reply flow

## Manual Verification

The following manual checks were completed locally:

- backend startup on `127.0.0.1:8000`
- frontend startup on `localhost:4173`
- login with bootstrap account
- tenant, overview, audit-log, and account API access
- real Bilibili QR login
- account bind success and credential refresh success

Observed real Bilibili integration result:

- QR login completed successfully
- account was persisted in the local database
- account refresh returned `active`
- target import preview returned an empty list for the tested account

This means the login integration is working, but the tested account did not expose importable video targets at that time.

## Remaining External Validation Gaps

- Docker image build and runtime were not revalidated because the local Docker daemon was unavailable.
- Full live comment polling and live reply sending were not completed against a real video target because no importable target was available from the tested account.

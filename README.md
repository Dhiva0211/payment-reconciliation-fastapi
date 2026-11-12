# Banking Payment Reconciliation & Exception Tracking (FastAPI)

[![CI](https://github.com/Dhiva0211/payment-reconciliation-fastapi/actions/workflows/ci.yml/badge.svg)](https://github.com/Dhiva0211/payment-reconciliation-fastapi/actions/workflows/ci.yml)

A Python / FastAPI service that loads payment records and bank settlement data, reconciles them, and exposes the exceptions — missing settlements, orphan settlements, amount/currency mismatches, and duplicate transactions — through documented, role-protected REST endpoints.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · PostgreSQL · Pydantic v2 · JWT (PyJWT) · bcrypt · Pytest · Ruff · Docker · GitHub Actions

## Endpoints

Interactive OpenAPI docs are served at `/docs`.

| Method | Path | Roles | Purpose |
|---|---|---|---|
| POST | `/auth/token` | — | OAuth2 password flow → JWT |
| POST | `/reconciliation/payments` | operator, admin | Bulk-load payments (validated: positive 2-dp amounts, ISO currency) |
| POST | `/reconciliation/settlements` | operator, admin | Bulk-load settlement lines |
| POST | `/reconciliation/runs` | admin | Reconcile and store exceptions; returns a summary |
| GET | `/reconciliation/exceptions?status=&run_id=&page=&size=` | analyst, admin | Paginated, filterable exception list |

## Design notes

- **Reconciliation logic is pure Python** (`app/reconciliation.py`) with no database code, so the matching rules are unit-tested in isolation.
- Amounts are `Decimal` end to end — `100.0` and `100.00` match; floats are never used for money.
- **Indexes** on `reference` (payments, settlements) and on `status` / `run_id` (exceptions) keep lookups and filtered exception searches fast as volumes grow.
- **Pagination** with `page`/`size` (max 500) and a total count.
- **Role-based authorization** through a `require_roles(...)` FastAPI dependency; admin passes every check.

## Run locally

```bash
docker compose up --build          # PostgreSQL + API on :8000
# or
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Try it with a realistic batch of **1,500 payments** (with seeded missing, mismatched, duplicate, and orphan records):

```bash
python scripts/generate_sample_data.py > sample.json
TOKEN=$(curl -s -X POST localhost:8000/auth/token -d 'username=admin&password=password' | jq -r .access_token)
jq '{items: .payments}'    sample.json | curl -s -X POST localhost:8000/reconciliation/payments    -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @-
jq '{items: .settlements}' sample.json | curl -s -X POST localhost:8000/reconciliation/settlements -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @-
curl -s -X POST localhost:8000/reconciliation/runs -H "Authorization: Bearer $TOKEN"
```

## Tests

```bash
pytest -q        # 18 tests
```

- `test_reconciliation.py` — 7 unit tests for the matching rules
- `test_security.py` — 3 tests for JWT issue/verify and password checks
- `test_api.py` — 8 integration tests through FastAPI's `TestClient` against an in-memory database: auth (401/403), validation (422), a full reconciliation run, pagination and filtering

GitHub Actions runs Ruff and the full test suite on every push and pull request.

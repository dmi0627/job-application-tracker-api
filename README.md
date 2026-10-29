# Job Application Tracker API

A REST API and lightweight web dashboard for tracking job applications through
their funnel — `wishlist → applied → oa → interview → offer / rejected /
withdrawn` — built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**
(SQLite locally), with a **pytest** suite and **Docker Compose** setup.

I built this while running my own new-grad SDE job search, and I use it to
track my real applications (the seed data is my actual search: 41 applications).

## Quick start

### Local (SQLite, zero setup)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python seed.py                       # load seed.json into the database
uvicorn app.main:app --reload        # http://127.0.0.1:8000
```

Interactive API docs (auto-generated OpenAPI): <http://127.0.0.1:8000/docs>

Web dashboard: <http://127.0.0.1:8000/>

The dashboard uses the same API and database. It provides summary statistics,
a visual status funnel, company/status filters, sorting, pagination, an
add-application form, inline status changes, and delete actions. It is plain
HTML/CSS/JavaScript served by FastAPI, so there is no separate frontend build
step.

### Docker (PostgreSQL)

```bash
docker compose up --build
```

This starts PostgreSQL 16 and the API on port 8000, wired together via
`DATABASE_URL`. Data persists in a named volume.

## Tests

```bash
pytest -q    # 11 tests, in-memory SQLite, no setup needed
```

## API overview

| Method | Path | Description |
| ------ | ---- | ----------- |
| GET | `/health` | Liveness check |
| POST | `/applications` | Create an application (201) |
| GET | `/applications` | List with filters, sorting, pagination |
| GET | `/applications/{id}` | Fetch one |
| PATCH | `/applications/{id}` | Partial update (e.g. move status forward) |
| DELETE | `/applications/{id}` | Delete (204) |
| GET | `/stats` | Totals by status, last 7/30 days, response rate |

List query parameters: `status`, `company` (case-insensitive substring),
`applied_after`, `applied_before`, `sort` (`date_desc` / `date_asc` / `company`),
`page`, `page_size`.

### Example

```bash
curl -X POST http://127.0.0.1:8000/applications \
  -H 'Content-Type: application/json' \
  -d '{"company": "Stripe", "role": "Software Engineer, Early Career",
       "location": "San Francisco, CA", "status": "applied"}'

curl 'http://127.0.0.1:8000/applications?status=interview'
curl http://127.0.0.1:8000/stats
```

## Design notes

- **Models vs schemas:** SQLAlchemy models (`app/models.py`) and Pydantic
  schemas (`app/schemas.py`) are separate on purpose — the storage layer and
  the API contract can change independently. Validation (required fields,
  non-negative salaries, status enum) happens at the schema layer, so bad
  input gets a 422 before it ever touches the database.
- **One session per request:** the `get_db` dependency opens and always
  closes a session per request; tests swap it out via FastAPI's
  `dependency_overrides` to run against an in-memory database.
- **Status as an enum:** the funnel stages are a Python `Enum` mapped to a
  database enum, so invalid states are impossible to store.
- **Stats computed in SQL:** `/stats` uses aggregate queries (`GROUP BY`
  status, date-window counts) instead of loading rows into Python.
- **Same code, two databases:** everything environment-specific goes through
  `DATABASE_URL`; SQLite locally and in tests, PostgreSQL in Docker.

## Project layout

```
app/
  main.py       # routes: dashboard, CRUD, filtering/pagination, /stats, /health
  models.py     # SQLAlchemy tables + ApplicationStatus enum
  schemas.py    # Pydantic request/response shapes
  database.py   # engine, session factory, get_db dependency
  static/       # dashboard HTML, CSS, and vanilla JavaScript
tests/
  test_api.py   # 11 end-to-end API/frontend tests
seed.py         # idempotent loader for seed.json
seed.json       # real application data (41 applications)
Dockerfile, docker-compose.yml
```

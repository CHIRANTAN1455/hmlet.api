# Property Management System API

A REST API for managing properties, units, tenants and rental contracts, built with
Django 5 + Django REST Framework, PostgreSQL and JWT authentication.

---

## Tech stack

| Concern | Choice |
| --- | --- |
| Language / framework | Python 3.12, Django 5.1, Django REST Framework 3.15 |
| Database | PostgreSQL 16 (SQLite supported as a fallback) |
| Auth | `djangorestframework-simplejwt` |
| Filtering | `django-filter` |
| API docs | `drf-spectacular` (OpenAPI 3, Swagger UI, ReDoc) |

---

## Quick start

### 1. Prerequisites

- Python 3.12+
- PostgreSQL 16 — via Docker (easiest) or a local install

### 2. Get the code

```bash
git clone https://github.com/CHIRANTAN1455/hmlet.api.git
cd hmlet.api
```

### 3. Start the database

**Option A — Docker (recommended):**

```bash
docker compose up -d
```

Starts PostgreSQL 16 on `localhost:5432` with the database, user and the
`btree_gist` extension already created.

**Option B — local PostgreSQL:**

```bash
createuser  --createdb --pwprompt pms          # password: pms
createdb    -O pms property_management
psql -d property_management -c "CREATE EXTENSION IF NOT EXISTS btree_gist;"
```

**Option C — no PostgreSQL at all:** skip this step and use the SQLite fallback
(see [Database](#database) for the one behavioural difference).

### 4. Install dependencies

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 5. Configure the environment

```bash
cp .env.example .env
```

The defaults in `.env.example` match the Docker Compose database, so this works
as-is. Generate a real secret key for anything beyond local use:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

### 6. Migrate and run

```bash
python manage.py migrate
python manage.py runserver
```

The API is now on **http://localhost:8000**.

### 7. Load demo data

```bash
python manage.py seed_demo
```

Creates 3 properties, 9 units, 5 members and 7 contracts, plus a staff login:

```
demo@hmlet.com / DemoPass123!
```

The contracts are a deliberate spread — currently active, expired, upcoming,
one pair running back-to-back, and one with a part-month tail — so every query
in the brief returns something meaningful, including `?active=true`.

Dates are relative to today rather than hard-coded, so the data still
demonstrates active-vs-expired whenever you run it. Re-running is safe; add
`--reset` to start clean.

---

## Interactive API docs

With the server running:

| URL | What it is |
| --- | --- |
| http://localhost:8000/api/docs/ | **Swagger UI** — browse and execute every endpoint |
| http://localhost:8000/api/redoc/ | ReDoc — cleaner read-only reference |
| http://localhost:8000/api/schema/ | Raw OpenAPI 3 schema (YAML) |

**To call protected endpoints from Swagger UI:**

1. Run `POST /api/auth/login` with `{"email": "demo@hmlet.com", "password": "DemoPass123!"}`
2. Copy the `access` value from the response
3. Click **Authorize** (top right) and enter `Bearer <access_token>`

The token then applies to every request you make from the page.

**Postman:** import `http://localhost:8000/api/schema/` — Postman reads the
OpenAPI schema and generates a collection covering every endpoint. Set an
`Authorization` header of `Bearer <access_token>` at the collection level.

---

## Endpoints

Every endpoint except register, login and the docs requires
`Authorization: Bearer <access_token>`.

### Auth

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/register` | Create a staff user, returns user + tokens |
| `POST` | `/api/auth/login` | Exchange credentials for a token pair |
| `POST` | `/api/auth/refresh` | New access token from a refresh token |
| `GET` | `/api/auth/me` | The authenticated user |

### Properties

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/properties` | Create a property |
| `GET` | `/api/properties` | List properties |
| `GET` | `/api/properties/{property_id}` | One property, with its units |

### Units

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/properties/{property_id}/units` | Add a unit to a property |
| `GET` | `/api/units` | List units — `?status=available`, `?property={id}` |

### Members

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/members` | Create a tenant |
| `GET` | `/api/members` | List tenants — `?search=` |

### Contracts

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/contracts` | Create a contract |
| `GET` | `/api/contracts` | List contracts — `?unit={id}`, `?member={id}` |
| `GET` | `/api/contracts?active=true` | Only contracts covering today |
| `GET` | `/api/contracts/{contract_id}` | One contract |

Full request and response samples for every endpoint — including the failure
cases — are in [`docs/API.md`](docs/API.md). Each one was captured from a live
server rather than written by hand.

---

## Design decisions

These are the judgement calls the brief left open. Documented here rather than
buried in code, since reasonable people would choose differently.

### Contract end dates are inclusive

A contract running `2026-01-01 → 2026-12-31` covers 31 December and is 12 months
long, not 11 months and 30 days.

### Total contract value

Computed from whole months plus a pro-rated remainder:

```
delta = relativedelta(end_date + 1 day, start_date)   ->  months, days
total = monthly_rent * months
      + monthly_rent * (days / days_in_that_month)     # partial month, pro-rated
```

Everything uses `Decimal` and is quantised to 2 decimal places with
`ROUND_HALF_UP` — floats are never used for money.

| Start | End | Months | Total (rent = 1000) |
| --- | --- | --- | --- |
| 2026-01-01 | 2026-12-31 | 12 | 12,000.00 |
| 2026-01-15 | 2026-07-14 | 6 | 6,000.00 |
| 2026-01-01 | 2026-01-15 | 0 + 15 days | 483.87 (`1000 × 15/31`) |

`total_value` is stored on the row rather than computed per request, so it can be
aggregated in SQL. It is recalculated by the service layer on every write.

### Double-booking prevention

Enforced in three layers, because a validation check alone is a race condition —
two simultaneous requests can both pass validation before either commits.

1. **Serializer validation** → `400` naming the conflicting contract. Good errors.
2. **`select_for_update()` inside `transaction.atomic()`** → concurrent creates
   for the same unit are serialised.
3. **PostgreSQL exclusion constraint** → the actual guarantee:

   ```sql
   EXCLUDE USING gist (unit_id WITH =, daterange(start_date, end_date, '[]') WITH &&)
   ```

   Overlapping contracts are rejected by the database itself, whatever the
   application does. The resulting `IntegrityError` is translated to a clean
   `409 Conflict`.

Two contracts overlap when `existing.start_date <= new.end_date` **and**
`existing.end_date >= new.start_date`.

### Unit status is derived, not set by hand

A unit is `occupied` if and only if a contract covers **today**. There is no
endpoint to set the status directly — it is recalculated whenever a contract
changes. A future-dated contract does not occupy a unit yet.

One honest caveat: a contract that ended yesterday should free its unit today,
but no request wrote to the database overnight. A management command handles it:

```bash
python manage.py sync_unit_statuses
```

In production this would run on a schedule (cron / Celery beat). Flagging it
rather than pretending the derived value is self-maintaining.

### Contracts have no cancellation

"Active" is purely date-derived, matching the brief exactly. Cancellation would
need a status field, a state machine and its own endpoint — noted here as the
obvious extension point rather than shipped half-finished.

---

## Database

A single `DATABASE_URL` selects the backend, so both work from identical code:

```bash
DATABASE_URL=postgres://pms:pms@localhost:5432/property_management   # preferred
DATABASE_URL=sqlite:///db.sqlite3                                    # fallback
```

**PostgreSQL is the target.** The exclusion constraint above is Postgres-only, so
on SQLite the migration that adds it is skipped and double-booking prevention
falls back to layers 1 and 2 (application-level). That is fine for a
single-process dev server and not fine under real concurrency — hence the
preference.

---

## Project structure

Organised by business domain rather than by technical layer: everything about
contracts lives in one place, instead of being scattered across global
`models.py` / `views.py` / `serializers.py` files.

```
.
├── config/                  # settings (base/dev/prod), root urls, wsgi/asgi
├── apps/
│   ├── common/              # TimeStampedModel, pagination, error envelope
│   ├── accounts/            # staff user, registration, JWT login
│   ├── properties/          # Property + Unit
│   ├── members/             # tenants
│   └── contracts/           # contracts — the domain logic lives here
├── docs/API.md              # captured request/response samples
├── scripts/                 # database bootstrap SQL
├── docker-compose.yml
└── .env.example
```

Within each app:

| File | Responsibility |
| --- | --- |
| `models.py` | Schema and database constraints |
| `serializers.py` | Validation and representation (read/write split) |
| `services.py` | **Business logic** — transactions, calculations, invariants |
| `views.py` | HTTP only; thin, delegates to services |
| `filters.py` | Query-parameter filtering |

Views deliberately stay thin. Anything with a rule in it — computing contract
value, rejecting an overlap, recalculating unit status — belongs in `services.py`
where it can be tested and reused without an HTTP request.

---

## Conventions

**Consistent error envelope.** Every failure has the same shape, so clients need
one code path rather than three:

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request payload failed validation.",
    "details": { "end_date": ["End date must be on or after start date."] }
  }
}
```

**Status codes:** `400` malformed or invalid, `401` missing/expired token,
`404` not found, `409` conflicts with existing state (double-booking).

**Pagination** on every list endpoint — 20 per page, `?page=` and `?page_size=`
(max 100), with `count` and `total_pages` in the body.

**Query efficiency.** List endpoints use `select_related` / `prefetch_related` so
the query count stays flat as the result set grows.

---

## Management commands

| Command | Purpose |
| --- | --- |
| `python manage.py seed_demo [--reset]` | Populate demo properties, units, members and contracts |
| `python manage.py sync_unit_statuses [--date YYYY-MM-DD]` | Recalculate unit availability from contract dates |
| `python manage.py createsuperuser` | Admin access at `/admin/` |

`sync_unit_statuses --date` evaluates as at an arbitrary date, which makes the
calendar-rollover behaviour easy to demonstrate without waiting for time to
pass:

```bash
python manage.py sync_unit_statuses --date 2030-01-01
```

---

## What has been verified

Behaviour claimed in this README was checked against a running server, not
assumed:

- **Contract value** — 8 cases including leap-year February and a pro-rata tail
  whose denominator changes with the month
- **Overlap rejection** — exact, partial and fully-contained overlaps rejected;
  adjacent ranges (starting the day after another ends) correctly allowed
- **Concurrency** — 6 simultaneous identical contract requests for the same unit
  produced exactly one `201` and five `409`s, with one row committed
- **Database guarantee** — a direct ORM insert bypassing all application
  validation was rejected by the PostgreSQL exclusion constraint
- **Unit status** — flips to `occupied` on contract creation and back to
  `available` once no contract covers the evaluation date
- **Query counts** — 23 units serialise in 1 query; properties with annotated
  unit counts in 1 query

---

## Environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | insecure dev value | Required in production |
| `DJANGO_DEBUG` | `True` in dev | |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | |
| `DATABASE_URL` | SQLite | Postgres URL preferred |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60` | |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | `7` | |

---

## Troubleshooting

**`connection refused` on port 5432** — the database is not up. Run
`docker compose up -d`, or fall back to SQLite by setting
`DATABASE_URL=sqlite:///db.sqlite3` in `.env`.

**`extension "btree_gist" does not exist`** — connect to the database and run
`CREATE EXTENSION btree_gist;`. Docker Compose does this automatically on first
boot; a pre-existing volume created before this file was added will not have it.

**`401 Unauthorized` everywhere** — expected. Register or log in, then send
`Authorization: Bearer <access_token>`.

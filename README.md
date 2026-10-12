# PitchPilot AI

See `SPEC.md` for the full project specification.

This repository is in **Phase 1 (Step 1.1)**: PostgreSQL-backed lead
management CRUD, using **Supabase-hosted PostgreSQL** as the primary
database. No AI integration, research agents, embeddings, or pitch
generation exist yet.

## Prerequisites

- Node.js 20+ and npm
- Python 3.12 (the backend venv is pinned to `>=3.12,<3.14`)
- [`uv`](https://docs.astral.sh/uv/) for Python dependency management
- A Supabase project (for the primary/development database)
- PostgreSQL 16 native Windows install (recommended for the **test**
  database only, so the automated test suite never touches Supabase ---
  see step 2 below)

## 1. Configure the Supabase connection (primary database)

1. Open your project at [supabase.com](https://supabase.com/dashboard).
2. Go to **Project Settings -> Database -> Connection string**.
3. Select the **Session pooler** tab (not "Direct connection" --- the
   direct connection requires IPv6, which most home/office networks and
   Windows setups don't have; the session pooler works over IPv4 and
   behaves like a normal Postgres connection, which Alembic needs for
   migrations). It looks like:
   ```
   postgresql://postgres.<project-ref>:[YOUR-PASSWORD]@aws-0-<region>.pooler.supabase.com:5432/postgres
   ```
4. Copy it, then build your `DATABASE_URL`:
   - Change the `postgresql://` prefix to `postgresql+psycopg://` (so
     SQLAlchemy uses the psycopg3 driver already in `pyproject.toml`).
   - Replace `[YOUR-PASSWORD]` with your actual database password,
     **URL-encoding** any special characters in it (see below).
   - Append `?sslmode=require` (Supabase requires SSL).
5. Put the result in `backend/.env` as `DATABASE_URL` (see step 3).

**URL-encoding a password with special characters** --- in PowerShell:

```powershell
[uri]::EscapeDataString('your-actual-password')
```

Use the output in place of the raw password in the connection string.

**Security notes:**
- Use the database password from Project Settings -> Database, **not**
  the `anon` or `service_role` API key --- those are for Supabase's REST/
  client SDKs, not for a raw PostgreSQL connection, and must never be
  used as a database password.
- Never put this connection string in a `NEXT_PUBLIC_*` variable or
  anywhere the frontend/browser can read it. It belongs only in
  `backend/.env`.
- If you don't have a Supabase project yet, or don't have its database
  password: create one (or reset the database password) from the
  Supabase dashboard yourself. Do not paste the password into chat with
  an AI assistant working on this repo --- only put it in `backend/.env`.

## 2. Configure the test database (local PostgreSQL, isolated from Supabase)

The test suite calls `Base.metadata.create_all()` / `drop_all()` against
whatever `TEST_DATABASE_URL` points to. To guarantee Supabase (your real
data) is never touched by a test run, point tests at the existing local
PostgreSQL 16 install instead of a second Supabase project:

```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -h localhost
```

At the `postgres=#` prompt:

```sql
CREATE ROLE pitchpilot WITH LOGIN PASSWORD 'choose-a-strong-local-password';
CREATE DATABASE pitchpilot_test OWNER pitchpilot;
\q
```

(If you already ran this during Step 1, you can reuse the existing role
and `pitchpilot_test` database.)

## 3. Configure the backend environment

Create `backend/.env` (gitignored, never committed) based on
`.env.example`:

```
BACKEND_CORS_ORIGINS=http://localhost:3000
DATABASE_URL=postgresql+psycopg://postgres.<project-ref>:<url-encoded-password>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
TEST_DATABASE_URL=postgresql+psycopg://pitchpilot:choose-a-strong-local-password@localhost:5432/pitchpilot_test
```

`DATABASE_URL` is optional at the application level --- `/health` still
works without it --- but every database-backed endpoint and the test
suite's lead tests require it (and will fail with a clear error, or skip
cleanly in tests, if it's missing). The test suite also refuses to run
(hard exit, not a silent skip) if `TEST_DATABASE_URL` is ever equal to
`DATABASE_URL`, since tests drop their tables at teardown.

## 4. Backend setup

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run pytest
uv run uvicorn app.main:app --reload --port 8000
```

- Health check (no DB required): http://localhost:8000/health
- DB readiness check: http://localhost:8000/health/db

### Inspecting and applying migrations

```powershell
cd backend
uv run alembic current         # show the currently applied revision
uv run alembic history         # list all revisions (works without a DB)
uv run alembic upgrade head    # apply all pending migrations
uv run alembic downgrade -1    # roll back one migration
```

The initial migration (`migrations/versions/9fbd56eca921_create_leads_table.py`)
creates the `leads` table and the `lead_status` enum type.

### Lead API examples

```powershell
# Create a lead
curl -X POST http://localhost:8000/api/v1/leads `
  -H "Content-Type: application/json" `
  -d '{"company_name":"Acme Corp","website":"https://acme.example.com","contact_email":"jane@acme.example.com"}'

# List leads (paginated, optional status filter)
curl "http://localhost:8000/api/v1/leads?page=1&page_size=20"
curl "http://localhost:8000/api/v1/leads?status=researching"

# Get one lead
curl http://localhost:8000/api/v1/leads/<lead_id>

# Update only the supplied fields
curl -X PATCH http://localhost:8000/api/v1/leads/<lead_id> `
  -H "Content-Type: application/json" `
  -d '{"status":"researching"}'

# Archive a lead (soft delete, not a permanent removal)
curl -X DELETE http://localhost:8000/api/v1/leads/<lead_id>
```

## Frontend (Next.js)

```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

- App: http://localhost:3000
- Configure the backend URL via `NEXT_PUBLIC_API_BASE_URL` in
  `frontend/.env.local` (defaults to `http://localhost:8000`).

## Running everything together

1. Supabase is always-on (hosted); no local step needed for `DATABASE_URL`.
   If running the test suite, make sure the local PostgreSQL 16 service
   (`postgresql-x64-16`) is running for `TEST_DATABASE_URL`.
2. `cd backend && uv run uvicorn app.main:app --reload --port 8000`
3. `cd frontend && npm run dev` (in a separate terminal)

The homepage shows a live backend connection status (loading, connected,
or error with a helpful message if the backend isn't running).

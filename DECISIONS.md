# Architecture & Security Decisions

This document records *why* things are built the way they are, not just
*what* was built (see `HANDOFF.md` for current state, `PROJECT_SPEC.md`/
`SPEC.md` for the original intended direction). Each entry is a decision
made at a point in time, not a universal truth — if circumstances change,
revisit it rather than treating it as fixed.

---

## Database: Supabase-hosted PostgreSQL, not local Postgres or Docker

**Decision:** Use Supabase as the primary (`DATABASE_URL`) database,
rather than a local PostgreSQL install or a Dockerized database.

**Why:** The project owner wanted to avoid installing/maintaining Docker
or a local Postgres server as a hard prerequisite, and chose Supabase as
the team's standing infrastructure choice. `SPEC.md`'s original
"free-first, local-first" framing listed local Postgres as the default
recommendation, but Supabase's free tier satisfies the same
zero-mandatory-cost constraint while being hosted.

**Status:** Decided and implemented.

---

## Backend connects as the Postgres role `postgres` (table owner), not a scoped app role

**Decision:** `DATABASE_URL` uses the project's default `postgres` role
(via Supabase's Session Pooler), which owns `public.leads`.

**Why:** This was the simplest path to get a working connection during
initial setup. It was not evaluated against the alternative of a
dedicated, lower-privilege application role.

**Consequence worth knowing:** Because `postgres` owns the table, it
automatically bypasses Row Level Security (see the RLS decision below)
unless `FORCE ROW LEVEL SECURITY` is set. This was *relied on*
intentionally when adding RLS (so the app wouldn't need any code change),
but it also means RLS provides no defense if something other than this
app's own backend code ever queries using the `postgres` role's
credentials.

**Status:** Decided and implemented. Not revisited — a lower-privilege
dedicated application role (with FORCE RLS and actual policies) could be
a future hardening step, not yet evaluated.

---

## Test isolation: dedicated schema + dedicated restricted role, not local Postgres or a second Supabase project

**Decision:** Automated tests run against `TEST_DATABASE_URL`, which
connects to the **same Supabase project** as production, but as a
separate, purpose-created role (`pitchpilot_test_runner`) scoped to a
separate schema (`pitchpilot_test`), using SQLAlchemy's
`schema_translate_map={None: "pitchpilot_test"}`.

**Alternatives considered and rejected:**
- *Local PostgreSQL for tests* — rejected because the project owner
  explicitly didn't want to install/maintain a second local database
  server just for tests.
- *A second, dedicated Supabase project for tests* — rejected as the
  default because it requires manual dashboard setup (new project
  creation) and introduces a second set of credentials to manage
  long-term, for a learning project where minimizing moving parts was
  preferred. (This remains a reasonable alternative if stronger
  physical isolation is ever wanted — it needs no code changes, since
  `conftest.py` already expects a distinct `TEST_DATABASE_URL`.)
- *SQLite or fully mocked sessions for everything* — rejected as the
  primary test strategy because the models use PostgreSQL-native `UUID`
  and `Enum` types; SQLite doesn't support these the same way, risking
  tests that pass against SQLite but fail against real Postgres (exactly
  the kind of drift the project wants to avoid). Mocking is used, but
  narrowly — only for pure request-validation tests where the database
  is never actually reached (see below).

**Why this design is safe (two independent layers, not just one):**
1. **Soft/application layer:** `schema_translate_map` rewrites every
   unqualified table/type reference to `pitchpilot_test` at SQL-compile
   time — not a session-level `SET search_path`, so it's immune to
   connection-pool state leaking between requests.
2. **Hard/database layer:** `pitchpilot_test_runner` has zero SQL
   privileges on `public` — confirmed empirically (every
   `has_table_privilege`/`has_schema_privilege` check returned `False`
   for every DML verb), not just assumed. Even if the `schema_translate_map`
   were accidentally removed from the code, the role itself cannot reach
   `public.leads`.

A hard safety guard also exists in `conftest.py`: if `TEST_DATABASE_URL`
is ever equal to `DATABASE_URL`, the test session refuses to run at all
(`pytest.exit`), since the fixture calls `Base.metadata.drop_all()` at
teardown and a misconfigured `.env` must never risk dropping production
tables.

**Status:** Decided, implemented, and verified end-to-end (role/schema
creation → permission checks → pooler login → schema-scoped table
creation → full pytest run → cleanup confirmation).

---

## Mixed test strategy: mocked DB session for pure validation, real Postgres for persistence

**Decision:** Split the lead-API test suite into two files —
`test_leads_validation.py` (uses a `MagicMock` standing in for the DB
session, never opens a network connection) and `test_leads.py` (uses the
real, schema-isolated Postgres connection).

**Why:** FastAPI validates the Pydantic request body *before* the
endpoint function body runs, so any test expecting a `422` from a
malformed payload never reaches the database layer at all —
mocking the session for exactly those tests means they can run with zero
database dependency, without sacrificing realism (they're not testing
anything the mock could get wrong). Tests that need the endpoint body to
actually execute (persistence, pagination, 404-on-missing-row lookups)
deliberately stay on real Postgres, rather than mocking SQLAlchemy query
behavior, to avoid tests passing against mock behavior that drifts from
what Postgres actually does.

**Status:** Decided and implemented.

---

## RLS enabled on `public.leads` with zero policies, no FORCE

**Decision:** `ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY` (via
migration `92142a5684c8`), with no policies defined and `FORCE ROW LEVEL
SECURITY` deliberately left off.

**Why:** An audit found `public.leads` had RLS disabled and broad SQL
grants (`SELECT/INSERT/UPDATE/DELETE/TRUNCATE`) to Supabase's `anon` and
`authenticated` roles — the defaults Supabase applies to every new table
in `public`. Combined with `public` very likely being exposed via
Supabase's auto-generated Data API (the project default; not
independently confirmed — see `HANDOFF.md`), this meant anyone holding
the project's `anon` key could potentially read/write/truncate every
lead record directly over REST, completely bypassing the FastAPI
backend's validation and business logic.

Enabling RLS with **zero policies** is the smallest possible fix: it
makes Postgres deny all access by default to any role that doesn't
bypass RLS. Since the backend connects as `postgres` (the table's
owner), and owners bypass RLS automatically unless `FORCE ROW LEVEL
SECURITY` is also set, this was verified to have **zero effect on the
running application** (confirmed via a live INSERT/SELECT sanity check
immediately after applying the migration).

**Alternatives considered and not chosen (for now):**
- Explicit `REVOKE` of grants from `anon`/`authenticated` — considered
  a viable *additional* layer, not applied, since RLS alone already
  achieves the same practical effect and is Supabase's idiomatic
  approach.
- Removing `public` from Supabase's Exposed Schemas API setting — the
  most complete fix, but requires dashboard access this session didn't
  have the context to perform/verify; left as an open item.

**Explicitly unresolved:** Whether `public` is actually reachable via
the Data API was never independently confirmed (would require testing
with the project's `anon` key, which should not be requested in chat).
RLS with zero policies protects against this regardless of the answer,
but the question itself is still open — see `HANDOFF.md`'s pending list.

**Status:** Decided and implemented. Explicitly flagged: do not add
policies, enable FORCE, change grants further, or touch Supabase API
settings without a separate, dedicated review — each has different risk
implications not yet evaluated.

---

## Credential handling: generated secrets are never echoed, and tool output is filtered

**Decision:** When a new database password needs to be generated (e.g.
for `pitchpilot_test_runner`), it's generated locally, embedded directly
into SQL text for the one statement that needs it, written straight into
`backend/.env`, and never printed to chat or captured in verbose tool
output. Statements containing a password are wrapped so a failure can't
leak it via a traceback (Postgres echoes the failing statement back in
error messages).

**Why:** Earlier in this project's history, a password was briefly
exposed in a SQLAlchemy exception traceback (parameters are included in
error messages) during initial setup. That password was for a role that
failed to actually get created (the statement itself failed first), so
no live credential was compromised, but the lesson was applied going
forward: never run DDL that embeds a secret without first confirming the
failure path can't leak it, and prefer `--tb=no`/filtered output for any
command that might touch a real connection string.

**Status:** Ongoing practice, not a one-time fix — apply this reasoning
to any future credential-generating step.

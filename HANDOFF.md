# Handoff — Current Verified State

**As of:** 2026-10-12
**Repository:** `D:\leadtoclients\`

This document separates four categories of information:
- ✅ **Confirmed** — directly re-verified in this session, right before writing this document.
- 📋 **Reported (not rechecked this session)** — stated as a result in a prior work session on this project; plausible and consistent with other evidence, but not independently re-run just now.
- ⚠️ **Assumption / unverified** — believed true but not checked by any tool, or explicitly flagged as unconfirmed in a prior audit.
- ⬜ **Pending / outstanding** — known work not yet done.

Do not treat anything outside the ✅ category as guaranteed without rechecking it yourself.

---

## Project and environment

- Repository path: `D:\leadtoclients\` ✅
- Frontend: Next.js 16.4.0, React 19.3.0, TypeScript, Tailwind CSS 4 ✅ (confirmed via `frontend/package.json`)
- Backend: FastAPI, Pydantic 2.x, SQLAlchemy 2.x, Alembic, `psycopg[binary]` (psycopg3) ✅ (confirmed via `backend/pyproject.toml`)
- Python 3.12.14 selected for the backend virtual environment (`backend/.venv`), via `uv` ✅
- Supabase PostgreSQL is the primary database (`DATABASE_URL`) ✅
- **LangGraph and the AI research/pitch-generation workflow described in `SPEC.md` are NOT implemented.** No `app/graph/`, `app/agents/`, `app/tools/`, or `app/retrieval/` directories exist in this repository. Do not assume any part of the agentic workflow exists beyond what's listed below. ✅ (confirmed by directory listing)

## Completed and verified (backend)

- `GET /health` — returns `{"status": "ok", "service": "pitchpilot-api"}`, no database dependency. ✅ (confirmed: file exists at `backend/app/main.py`, matches description)
- `GET /health/db` — database readiness check, returns 503 (not a raw exception) if the database is unreachable. ✅ (confirmed by reading `backend/app/main.py`)
- Frontend `BackendStatus` component at `frontend/src/components/BackendStatus.tsx` calls `/health` and shows loading/connected/error states. 📋 (built and browser-verified in an earlier session; not re-tested in a live browser this session)
- Lead CRUD API under `/api/v1/leads` (`POST`, `GET` list with pagination + status filter, `GET /{id}`, `PATCH /{id}` partial update, `DELETE /{id}` → soft-archive, not a hard delete). ✅ (confirmed: `backend/app/api/v1/leads.py` exists with these exact routes)
- `Lead` SQLAlchemy model at `backend/app/models/lead.py`, with statuses: `new`, `researching`, `researched`, `pitch_ready`, `archived`. ✅
- `LeadStatus` enum column uses `values_callable=lambda enum_cls: [e.value for e in enum_cls]` — this was a real bug fix: without it, SQLAlchemy sends each Python member's `.name` (`"NEW"`) instead of `.value` (`"new"`), which doesn't match Postgres's actual lowercase enum labels and would make every INSERT fail. ✅ (confirmed by reading the current file; the fix is present)
- Two Alembic migrations exist, chained `9fbd56eca921 -> 92142a5684c8`:
  - `9fbd56eca921` — creates `leads` table + `lead_status` enum + `ix_leads_status` index.
  - `92142a5684c8` — `ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY` (no policies, `FORCE ROW LEVEL SECURITY` left off).
  - ✅ Chain confirmed via `uv run alembic history` this session.
- **Production Supabase state, freshly re-checked this session (not just reported from a prior stage):**
  - Current Alembic revision: `92142a5684c8` (head). ✅
  - `public.leads`: RLS enabled = `True`, FORCE RLS = `False`, policy count = `0`. ✅

## Test infrastructure

- `TEST_DATABASE_URL` points to a dedicated, privilege-restricted Postgres role `pitchpilot_test_runner`, scoped to a `pitchpilot_test` schema in the **same Supabase project** as production. 📋
- This role has zero privileges on `public` (verified in a prior session via `has_table_privilege`/`has_schema_privilege` checks against every DML verb) and its `search_path` is pinned to `pitchpilot_test` only. 📋
- `backend/tests/conftest.py`'s `test_engine` fixture builds its engine exclusively from `TEST_DATABASE_URL`, with `schema_translate_map={None: "pitchpilot_test"}`, and has a hard `pytest.exit()` guard if `TEST_DATABASE_URL` is ever equal to `DATABASE_URL`. ✅ (confirmed by reading the current file)
- Test files: `test_health.py` (no DB), `test_leads_validation.py` (7 tests, mocked DB session via `unittest.mock.MagicMock`, never opens a network connection), `test_leads.py` (11 tests, real Postgres via `pitchpilot_test_runner`). ✅ (confirmed by directory listing + file contents)
- **Latest reported full test result: 19 passed, 0 failed, 0 errors, 0 skipped.** 📋 — this was the result of the last `uv run pytest -v` run in the prior session, immediately after the RLS migration was applied and the test schema was confirmed cleaned up afterward (0 tables remaining in `pitchpilot_test`). Not re-run in this session, since this task is documentation-only and instructed not to change application/database state.

## Security and database cautions

- **Never run tests against `DATABASE_URL` or production `public`.** Tests must only ever use `TEST_DATABASE_URL` → `pitchpilot_test_runner` → `pitchpilot_test` schema.
- **Never use `DROP SCHEMA`, `CASCADE`, or broad cleanup against production.** Test cleanup (`Base.metadata.drop_all()`) is scoped to `pitchpilot_test` only via `schema_translate_map`; it is never applied to `public`.
- ⚠️ **The Supabase Data API "Exposed Schemas" setting has not been independently confirmed.** A prior audit found `public.leads` had RLS disabled and broad `anon`/`authenticated`/`service_role` SQL grants (now fixed by enabling RLS — see above), but whether `public` is actually reachable over Supabase's REST API depends on a project-level dashboard setting (Settings → API → Exposed Schemas) that cannot be checked via SQL. This was never independently verified — it was assumed to still be at Supabase's default (which typically exposes `public`). The RLS fix mitigates the data-access risk regardless of this setting, since RLS with zero policies denies all non-owner access either way.
- **RLS is enabled on `public.leads` with zero policies.** This is intentionally minimal — it denies all access to non-owner roles (`anon`, `authenticated`, `service_role`) by default, without needing to define any policy. Do not casually add RLS policies, change the existing grants, enable `FORCE ROW LEVEL SECURITY`, or change Supabase API settings without a separate, explicit review — each of those has different blast-radius implications that haven't been evaluated.
- **The backend connects as `postgres`, the table owner, which bypasses RLS by default** (confirmed via a live INSERT/SELECT sanity check after the RLS migration was applied, in the prior session). This means RLS currently protects against the Data API / other non-`postgres` connections, but does **not** provide any application-level authorization — the FastAPI backend's own endpoints have no auth/authorization layer at all yet. Do not treat RLS as a substitute for that.
- **Never include credentials or secrets in documentation, commit messages, or chat.** Refer to environment variable names only (`DATABASE_URL`, `TEST_DATABASE_URL`, `BACKEND_CORS_ORIGINS`, `NEXT_PUBLIC_API_BASE_URL`) — never their values. This document contains none.

## Git state (verified in this session, right now)

- `git status`: **clean working tree**, branch `main`, up to date with `origin/main`.
- `git log --oneline`: two commits exist —
  - `4ac3148` — "Initial commit"
  - `757f2be` — "Complete lead backend foundation and secure RLS"
- Remote: `origin` → `https://github.com/DhruvChourey/Lead2Client.git` (both fetch and push).
- **Correction to a prior framing:** at the start of this task, the expectation was that "a second commit is being prepared manually" and might not exist yet. `git status`/`git log` show it already exists and the working tree is already clean — this document reports what was actually observed, not the prior expectation. Do not assume any particular commit state without running `git status`/`git log` yourself; this is a snapshot of one point in time.
- No staging, committing, pushing, or history rewriting was performed as part of writing this documentation.

## Pending / outstanding (not started)

- No authentication or authorization layer on the FastAPI backend itself.
- No independent confirmation of the Supabase Data API Exposed Schemas setting (see above).
- Organization/service-profile configuration (`SPEC.md` Phase 1 scope item) — not built.
- Everything from `SPEC.md` Phase 2 onward: LLM provider abstraction, research tools, embeddings/RAG, LangGraph workflow, scope/guardrail enforcement, strategy and content generation, PPTX/DOCX rendering, critic/evaluation stage, reliability/deployment hardening. None of this exists yet.
- Frontend has only a health-check homepage — no lead management UI (dashboard, lead form, list view) yet, despite the backend API existing.

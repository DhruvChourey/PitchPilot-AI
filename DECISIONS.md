# Architecture & Security Decisions

This document records *why* things are built the way they are, not just
*what* was built (see `HANDOFF.md` for current state, `PROJECT_SPEC.md`/
`SPEC.md` for the original intended direction). Each entry is a decision
made at a point in time, not a universal truth — if circumstances change,
revisit it rather than treating it as fixed.

---

## Premium dark theme is a fixed default, not `prefers-color-scheme`-driven

**Decision:** `globals.css` sets dark design tokens directly on `:root`
(no light-mode branch, no `@media (prefers-color-scheme: dark)`), rather
than the Phase 2 approach of light-by-default with `dark:` Tailwind
variants sprinkled through every component.

**Why:** The brief asked for a deliberate "premium, modern AI SaaS"
dark identity (comparable to Linear, Vercel, Raycast), not a theme that
happens to go dark when the OS prefers it. A fixed theme also halves
the class list on every component (no more parallel light/dark variants
of every color utility) and guarantees the accent gradient, status
badges, and card surfaces always render as designed, regardless of the
viewer's OS setting.

**Tradeoff accepted:** there's currently no light-mode option at all,
and no user-facing theme toggle. If that's wanted later, it's a
deliberate follow-up, not an oversight.

**Status:** Decided and implemented.

---

## Create/edit forms are a styled "panel", not a true modal or intercepting route

**Decision:** `/leads/new` and `/leads/[id]` remain full page routes
(as built in Phase 2), now styled as a centered card with rounded
corners, a drop shadow, and a GSAP fade+rise entrance — not converted
to an actual modal overlay or a Next.js intercepting route.

**Why:** The brief asked to animate the creation/edit "form modal or
drawer... when it opens and closes," which read as a request for that
*visual treatment*, not necessarily a literal modal architecture. Full
page routes keep the existing, already-tested navigation model intact
(shareable/bookmarkable edit URLs, working browser back button, no new
routing complexity) — directly serving the instruction to preserve
existing working functionality and make minimal, scoped changes. A true
modal/intercepting-route implementation is a larger, riskier
restructure that wasn't asked for explicitly enough to justify
reopening already-verified navigation behavior.

**Status:** Decided and implemented. Revisit only if a real modal
(e.g. create-without-leaving-the-list) is explicitly requested later.

---

## GSAP integration: `@gsap/react`'s `useGSAP` + a shared `Reveal` wrapper, not ad hoc `useEffect`

**Decision:** Installed the official `@gsap/react` package for its
`useGSAP()` hook, and built one reusable component (`Reveal.tsx`) that
every page's entrance animation goes through, rather than writing
`useEffect` + manual `gsap.context()`/`ctx.revert()` in each component.

**Why:** `useGSAP`'s `scope` option automatically reverts animations on
unmount (and handles React Strict Mode's double-invoke in development
correctly) — doing this by hand in every component is exactly the kind
of boilerplate that leads to memory leaks or animations conflicting
with React's own DOM updates, which the brief explicitly warned against.
Centralizing it in `Reveal` also means the `prefers-reduced-motion`
check (`lib/motion.ts`) and timing/easing constants live in one place,
not copy-pasted and potentially drifting across pages.

**Status:** Decided and implemented, used by the homepage, leads list
(including a second, independently re-triggerable stagger for the row
list), and both the create and edit panels.

---

## Next.js 16 dynamic routes: Server Component wrapper + `instant = false`, not `useParams()`

**Decision:** For `/leads/[id]`, `page.tsx` is an async Server Component
that awaits `params` and renders a Client Component (`LeadDetailClient.tsx`)
with `id` passed as a prop — rather than having the page itself be a
Client Component calling `useParams()`.

**Why:** Next.js 16 ships `cacheComponents` ("instant navigation"
validation) on by default. `useParams()` in a Client Component blocks
prerendering and can't be fixed with `export const instant = false`
(that export throws if used in a Client Component at all). Accessing
route `params` in a Server Component hits the same validation, but can
be explicitly opted out there. Since `/leads/[id]` always fetches a
specific record at runtime — there's no static shell to prerender — the
correct fix is `export const instant = false` on the Server Component
page, not fighting the framework with Suspense boundaries that don't fit
a single-record detail view.

**Applies to:** any future dynamic route (`[id]`, `[slug]`, etc.) added
to this frontend. Follow this same split, not `useParams()`.

**Status:** Decided and implemented, verified via `npm run build` actually
failing first, then succeeding after the fix (not assumed).

---

## List/filtered data fetching in effects: `useTransition` Actions, not manual loading state

**Decision:** `frontend/src/app/leads/page.tsx` uses React 19's
`useTransition` with an async function passed to `startTransition`
("Actions") to drive its loading state, rather than a manually-managed
`useState<"loading"|"loaded"|"error">`.

**Why:** `eslint-plugin-react-hooks`'s `set-state-in-effect` rule (new in
the version pulled in by Next.js 16) flags a synchronous `setState`
call at the top of a `useEffect` body — the natural way to reset to
"loading" before a refetch on page/filter change. `useTransition`'s
`isPending` is the React-sanctioned replacement: it doesn't trigger the
lint rule, and as a side benefit the previous list stays visible while
a new page/filter loads (no loading-flash on every click), rather than
being a strictly mechanical lint-silencing workaround.

**Applies to:** any future component that re-fetches data in an effect
keyed on changing dependencies (pagination, filters, search). Reach for
this pattern instead of a manual loading boolean.

**Status:** Decided and implemented.

---

## Manual browser QA against the test schema, via a temporary env override

**Decision:** When manually browser-testing the lead UI (Phase 2), the
dev backend was launched with `DATABASE_URL` temporarily overridden via
a process-scoped environment variable (never written to `backend/.env`)
to the `pitchpilot_test_runner` connection string, instead of the real
`DATABASE_URL`.

**Why:** The app's normal runtime code (`app/database.py`) has no
schema-translation logic — it relies on whatever `DATABASE_URL` points
to. Browser-clicking through create/edit flows against the real
`DATABASE_URL` would have written real (fake) lead records into
`public.leads`, and the API has no hard-delete endpoint, so that data
would persist permanently. Because `pitchpilot_test_runner`'s Postgres
`search_path` is already pinned server-side to `pitchpilot_test` (see
the dedicated-test-schema decision above), simply connecting as that
role for one dev-server process was sufficient — zero application code
changes needed, and `public.leads`'s row count was verified at `0` both
before and after the browser session.

**Applies to:** any future manual/exploratory browser testing that would
otherwise write data through the real backend. Prefer this pattern over
either touching production or adding test-mode branching to app code.

**Status:** One-off technique used for Phase 2 verification, not a
standing dev-server configuration — `backend/.env`'s actual
`DATABASE_URL` was never changed.

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

---

## RLS via a custom GUC (`app.current_user_id`) is defense-in-depth against app bugs, NOT a security boundary against SQL injection or arbitrary SQL execution

**Decision:** Lead ownership is enforced twice, independently: once in
FastAPI (`owner_id` filtering already present from Checkpoint 2) and
again at the database level via Postgres Row-Level Security, using a
custom session GUC (`app.current_user_id`) that the app sets once per
request in `get_current_user` (`app/core/rls.py`), read by the RLS
policy's `USING`/`WITH CHECK` clauses via `current_setting(...)::uuid`.

**Why this does NOT protect against SQL injection or arbitrary SQL
execution, stated explicitly before implementation (per your
requirement) and still true after implementation:** a custom GUC like
`app.current_user_id` is just a regular session variable. Any SQL
statement that runs *as* the `pitchpilot_app` (production) /
`pitchpilot_test_app` (test) role can call
`set_config('app.current_user_id', '<any-uuid>', ...)` itself and set it
to *any* value, including another user's id — there is nothing
preventing the role from forging it. The only way to make a custom GUC
genuinely un-settable by the connecting role is to register it from a
compiled C extension with `PGC_SUSET` (or stricter) context, which
requires `shared_preload_libraries` — not available on Supabase's
managed Postgres, and not attempted here. Concretely:
- If an attacker achieves arbitrary SQL execution as the app role (e.g.
  via a SQL injection bug elsewhere in the app), they can simply call
  `set_config('app.current_user_id', '<victim-uuid>', false)` and then
  read/write that victim's leads — RLS does not stop this, because the
  GUC itself is the attacker's own input at that point.
- What this design *does* protect against: a FastAPI code-level mistake
  — a forgotten `owner_id` filter, a new route that skips the ownership
  check added in Checkpoint 2, a future refactor that drops a `WHERE`
  clause. Even if the application code's own filtering is wrong or
  missing, the database still refuses to return/accept rows that don't
  match the GUC the *authentication dependency* set for this request.
  This is the actual, verified property — not a claim that RLS makes
  the app immune to injection.
- `users` and `sessions` are **not** RLS-protected by this design. Only
  `leads` has an owner column and a policy. This was a deliberate scope
  decision, not an oversight, but it means a code bug that queries
  `users`/`sessions` without a `WHERE` clause has no database-level
  backstop the way `leads` queries do.

**Why `set_config(name, value, is_local=true)` instead of `SET LOCAL
app.current_user_id = <value>`:** `set_config` is a normal SQL function,
so its `value` argument is passed as a regular bind parameter (`:uid`)
— no string interpolation of a UUID into SQL text, no injection surface
on *this* statement. `SET`/`SET LOCAL` are SQL commands, not function
calls, and don't reliably support parameter binding for their value the
same way. `is_local=true` gives the same transaction-scoped behavior as
`SET LOCAL`: the setting is cleared automatically at `COMMIT`/`ROLLBACK`
rather than persisting for the life of the physical connection — this
matters because `pitchpilot_app`/`pitchpilot_test_app` is a single
shared, pooled role used across every user's requests, so a value that
survived past one transaction could leak into the next request that
happens to reuse the same pooled connection.

**Verified by direct SQL-level tests (`backend/tests/test_rls.py`),
independent of the FastAPI app layer, exercising the restricted
`pitchpilot_test_app` role directly:**
- Correct context → own row visible; wrong context → zero rows (not an
  error, not someone else's data).
- `set_config(..., true)` set and committed in one transaction is
  **not** visible in a fresh transaction on the same physical
  connection — the required non-leakage property for a pooled role.
- A connection that has *never* called `set_config` for this GUC: on
  this specific Postgres/Supabase setup, `current_setting(..., true)`
  returns `''` (empty string), **not** SQL `NULL`, which is what
  textbook Postgres documentation on unset custom GUCs would suggest —
  confirmed empirically with a disposable brand-new engine with zero
  prior fixture activity, not assumed. Because the policy casts this
  value `::uuid`, an empty string fails the cast and the query raises a
  `DataError` rather than silently returning zero rows or (far worse)
  all rows. Net effect: forgetting to call `set_rls_user_context` fails
  *loud* (every leads query 500s) rather than failing open. This is a
  materially different failure mode than "empty result set" and is
  recorded precisely for that reason — see `HANDOFF.md`'s unresolved
  risks for Checkpoint 3.
- `pitchpilot_test_app` confirmed directly via `pg_roles`/`pg_class`:
  `rolbypassrls = false` and it does not own the `leads` table — so it
  cannot bypass RLS the way a table owner (`postgres`/
  `pitchpilot_test_runner`) automatically does.

**Test/production role separation:** `pitchpilot_test_runner` (owns the
`pitchpilot_test` schema's tables, used only for schema setup —
`CREATE TABLE`/`GRANT`/`CREATE POLICY`) vs. `pitchpilot_test_app`
(non-owner, `NOBYPASSRLS`, the role `db_session`/`client`/`second_client`
actually run queries through) mirrors the intended production split
(`postgres` admin vs. a future `pitchpilot_app` runtime role, authored
but not applied — see migration `b2b5b3f0c716`). Switching `db_session`
to the restricted role means every existing Checkpoint 2 ownership test
now implicitly doubles as an RLS enforcement test, confirmed by the full
suite passing unchanged (44 passed) after the switch.

**Status:** Decided and implemented for `leads` only. Explicitly flagged
as a defense-in-depth measure against application-code bugs, not a
security boundary against SQL injection/arbitrary SQL execution, and not
extended to `users`/`sessions`. The production-side role
(`pitchpilot_app`) and migration (`b2b5b3f0c716`) are authored for
review only — nothing has been applied to production.

---

## Mutating routes read server-generated columns from the same transaction that writes them, not a post-commit refresh

**Decision:** `create_lead`/`update_lead`/`archive_lead` (`app/api/v1/leads.py`) no longer call `db.refresh(lead)` after `db.commit()`. `app/database.py`'s `get_db()` session factory now sets `expire_on_commit=False`. Together these mean: everything the response needs (`id`, `created_at`, `updated_at`) is populated into the ORM object *before* commit ends the transaction, and nothing in the request queries the database again afterward.

**The bug this replaces, found by a Checkpoint 3 security review:** `set_rls_user_context` sets `app.current_user_id` via `set_config(..., true)` — deliberately transaction-scoped (see the RLS entry above). `db.commit()` ends that transaction, which clears the GUC. The old code then called `db.refresh(lead)`, which issues a fresh `SELECT` in a brand-new transaction — one where the GUC has reverted to `''` (Postgres's actual behavior here, not textbook `NULL` — see the RLS entry above), and the `leads_owner_isolation` policy's `::uuid` cast on `''` raises `DataError`. Confirmed empirically with a session built the same way `get_db()` actually builds one (bound directly to the Engine, no externally pre-opened transaction) against the real restricted role and policy. This was latent in production (which still connects as the RLS-bypassing `postgres` role) but would have broken every create/update/archive request the moment that changes.

**Why this fix, not "re-set the GUC after every commit":** re-setting the GUC after each commit treats the symptom at every call site that happens to commit-then-query — easy to forget on a future route, and it still spends two round-trip transactions on what's conceptually one atomic operation. The chosen fix removes the need for a post-commit query at all, which is correct independently of RLS: `created_at` (`server_default=func.now()`) and `updated_at` (`server_default=func.now()`, `onupdate=func.now()`) are server-evaluated SQL expressions, and SQLAlchemy (on backends that support `RETURNING`, which Postgres/psycopg does) automatically appends `RETURNING` to the `INSERT`/`UPDATE` statement it issues during `commit()`'s internal flush — *before* the transaction ends — and populates those values onto the Python object directly from that result. `db.refresh()` was always redundant for this, not just dangerous under RLS.

**Why `expire_on_commit=False` is also necessary, not just removing `refresh()`:** SQLAlchemy's Session default (`expire_on_commit=True`) expires every loaded attribute on commit, so the *next* attribute access — even an ordinary one, like FastAPI/Pydantic reading `lead.company_name` to build the `LeadRead` response — triggers an implicit lazy-reload `SELECT`, in a new transaction, with no code visibly "forgetting" a refresh. Removing the explicit `db.refresh()` call alone would not have fixed the bug; the implicit one SQLAlchemy inserts on your behalf would still have hit it. Since each FastAPI request gets its own freshly-created `Session` (`get_db()` builds one per request, never reused across requests), `expire_on_commit=False` carries none of the cross-request staleness risk it would have in a long-lived session — the object is simply correct for the remaining lifetime of this one request/response cycle.

**`get_db()` also gained an explicit `except Exception: db.rollback(); raise`** before its existing `finally: db.close()`. `Session.close()` already rolls back an uncommitted transaction on its own, so this isn't strictly new protection — it's made explicit so the rollback-on-error guarantee is visible in the code itself rather than relying on a reader knowing `close()`'s implicit behavior, and so a failed `commit()` can never leave a request's error response paired with partially-applied data: by the time any exception propagates out of a route, either nothing was committed (rolled back) or the commit had already fully succeeded before the exception point — and after this fix, nothing in these routes can fail *after* a successful commit, because nothing runs a query after it anymore.

**Why `app/core/sessions.py`'s identical-looking `db.commit(); db.refresh()` pattern (`create_session`, `revoke_session`) was deliberately left unchanged:** `users` and `sessions` have no RLS policy (by the original Checkpoint 3 scope decision — only `leads` is RLS-protected), so there is no GUC for a post-commit query on those tables to collide with. Changing them wasn't part of this bug and was out of scope for a minimal, targeted fix — but if `users`/`sessions` are ever given RLS policies in the future, this same class of bug would need the same fix applied there.

**Verified by regression tests using a production-faithful session lifecycle** (`backend/tests/test_rls_commit_regression.py`) — deliberately *not* using the existing `db_session`/`client` fixtures, which bind to an already-open external transaction and make `db.commit()` a no-op at the database level (masking this exact bug, which is how the original Checkpoint 3 suite passed 44/44 despite the bug being present). See that file's module docstring for the fixture design. Full backend suite re-run clean afterward — see `HANDOFF.md`.

**Status:** Fixed and verified against the real restricted role (`pitchpilot_test_app`) and the real `leads_owner_isolation` policy. Production is unaffected either way (still connects as `postgres`, which bypasses RLS) until the still-pending, separately-scoped role/connection switch happens — this fix removes what would otherwise have been a guaranteed outage at that point.

---

## Checkpoint 4 — CSRF: two differently-signed tokens, not one plain double-submit value

**Decision:** replaced the original placeholder (`app/core/csrf.py`'s `generate_csrf_token()` — an unsigned random string, compared only for cookie==header equality) with two distinct, HMAC-signed token flavors:

1. **Session-bound** (`sign_session_csrf_token`/`verify_session_csrf_token`): `hex(HMAC(SECRET_KEY, "session:" + session.hashed_token))`. No stored nonce — it's deterministically derived from the session's own `hashed_token` (already stored on `UserSession`, never the raw cookie value). Used for every authenticated mutating request: lead create/update/archive, logout.
2. **Pre-authentication** (`generate_preauth_csrf_token`/`verify_preauth_csrf_token`): `nonce.hex(HMAC(SECRET_KEY, "preauth:" + nonce))`, issued by a dedicated `GET /api/v1/auth/csrf-token` endpoint. Used for register/login, which run before any session exists.

**Why signed, not plain equality:** SameSite=Lax already blocks the session cookie from riding along on a cross-site fetch/XHR/form submission — the usual CSRF vector. The gap a plain double-submit token doesn't close is *cookie-tossing*: an attacker who controls a sibling or compromised subdomain of the same parent domain can often **set** (though not read) a cookie on that parent domain, even with SameSite=Lax in place. If the token were just a random value checked only for cookie==header equality, the attacker could toss a cookie of their own choosing and — separately, e.g. via a crafted same-site-permitted request — try to get that same chosen value echoed as the header, no server secret required. Signing with a server-only `SECRET_KEY` means the attacker can toss *a* cookie value but can't produce one that verifies, because they can't compute the HMAC.

**Why the session-bound flavor doesn't need a stored nonce, but the pre-auth one does:** after login there's already a per-session secret to bind to (`hashed_token`, unknown to anyone without the session's raw cookie). Before login there's no such secret yet, so the pre-auth token needs its own randomness (the nonce), with the signature only proving the *nonce* wasn't tampered with — the nonce itself still has to travel in the cookie, same shape as the original design, just now signed.

**Token lifecycle (resolved before implementing, per your request):**
- Pre-auth cookie: issued by `GET /api/v1/auth/csrf-token`, and *only* if the request doesn't already carry a valid one — this endpoint never regenerates an already-good cookie on every call (verified by `test_csrf_token_endpoint_does_not_regenerate_an_existing_valid_cookie`). It's a dedicated endpoint, not a blanket "seed on every response" middleware, so the cookie is set only where it's actually needed (before showing a login/register form) rather than on `/health`, lead routes, etc.
- Session-bound cookie: set directly by `login()` (`_set_session_csrf_cookie`), computed from the *new* session's `hashed_token`. This is also how rotation happens — a second login (new session, new `hashed_token`) always produces a different derived value, with no separate token store or explicit "rotate" step to remember; confirmed by `test_csrf_token_rotates_on_login`.
- On successful login, the pre-auth cookie is explicitly deleted (`response.delete_cookie`) — its job is done, and leaving it around risks it being mistaken for the (differently-signed) session-bound token.
- On logout, both the session cookie and the session-bound CSRF cookie are deleted, same as before.

**Origin/Referer policy:** `_verify_trusted_origin` (in `app/dependencies.py`) checks `Origin` against the exact configured `cors_origins_list` (no wildcard, no prefix/suffix match); if `Origin` is absent, falls back to `Referer`'s origin; if **both** are absent, the request is rejected. Chosen deliberately: a real browser performing a cookie-carrying fetch/XHR/form submission always sends at least one of these, so their total absence is itself the anomaly, not a case worth accommodating. Never trusts `X-Forwarded-*` — those headers are client-settable, and no reverse-proxy topology is known/configured for this project yet (flagged as an open deployment question in `HANDOFF.md`).

**Enforcement scope:** `verify_csrf_authenticated` is applied to `leads.py`'s POST/PATCH/DELETE and to `auth.py`'s `logout` (your explicit decision — consistent enforcement over exempting logout as "low severity"). `verify_csrf_preauth` is applied to `register` and `login`.

**Status:** Implemented and enforced everywhere decided above. Not implemented: frontend integration (calling `GET /auth/csrf-token` before rendering the login/register form, reading/echoing the header on fetch calls) — explicitly out of scope for this checkpoint, deferred to Checkpoint 5.

---

## Checkpoint 4 — rate limiting: hand-rolled, in-memory, explicitly not multi-instance-safe

**Decision:** added `app/core/rate_limit.py` — a small, dependency-free sliding-window limiter, rather than pulling in `slowapi`/`limits`. Reasoning: nothing comparable already exists in the stack (checked `pyproject.toml` first, per your instruction to inspect dependencies before adding new ones), the logic needed is genuinely small, and a hand-rolled limiter is trivial to make deterministically testable — each `RateLimiter` exposes a `.clock` attribute tests monkeypatch directly, so rate-limit tests advance a fake clock instead of sleeping through real windows.

**Keying — dual, independent limits, never an account lock:** every login/register request is checked against **two** separate buckets: per-IP (`request.client.host` — Starlette/uvicorn's own view of the peer, never `X-Forwarded-For` or similar, which this project doesn't trust without a known, configured proxy in front of it) and per-normalized-email (`.strip().lower()`, then SHA-256-hashed before use as the bucket key — the raw email is never stored in the limiter's own state, so a debug-time dump of it can't leak submitted addresses). Both are time-windowed throttles returning `429` + `Retry-After`; neither sets any persisted "locked" flag on the account. This matters specifically because a persisted lock keyed by email would be an attacker-triggerable DoS on a victim: repeatedly fail that victim's login a few times and they're locked out too. Throttling (which self-resets) doesn't have that failure mode.

Current thresholds: login — 10/minute per IP, 5/5 minutes per email; register — 5/minute per IP, 3/5 minutes per email. Chosen as a starting point generous enough not to block normal shared-IP usage (office NAT, etc.) while still bounding automated abuse; easy to retune later from this file alone.

**Known, accepted-for-now limitation — NOT claimed to be production-sufficient:** this state is a plain in-process dict. Running more than one backend instance means each instance enforces independent counters — an attacker spread across N instances effectively gets `limit × N`. A shared backend (Redis, via a `limits`-style `redis://` storage, or equivalent) is required before horizontal scaling becomes safe. Not implemented here because no such infrastructure is provisioned for this project yet; this is a deployment prerequisite to resolve before going multi-instance, not an oversight.

**Status:** Implemented for login/register only, as scoped. Deterministic tests cover per-IP threshold/429, per-email threshold/429, independence between the two keys, and window-reset-without-permanent-lockout behavior — see `backend/tests/test_rate_limit.py`.

---

## Checkpoint 5 — frontend auth state lives in one React context backed by a single real `/me` call, never a client-side boolean

**Decision:** `frontend/src/lib/auth.tsx`'s `AuthProvider` is the only place that knows "is anyone logged in." It starts in a `"loading"` state and calls `GET /api/v1/auth/me` exactly once on mount; a `200` becomes `"authenticated"` (with the returned user), a `401` becomes `"unauthenticated"`. There is no separate `isLoggedIn` flag anywhere, and nothing is ever written to `localStorage`/`sessionStorage` — not a token, not a boolean, not the user object.

**Why not a persisted boolean ("remember login across reloads locally"):** a client-side flag can drift from reality (the HttpOnly session cookie could have expired, been revoked server-side, or never existed if `localStorage` was copied/tampered with) and would then either show stale "logged in" UI against a session that's actually dead, or require its own invalidation logic that duplicates what the cookie+backend already do correctly. The actual session lives in an HttpOnly cookie the frontend can't read anyway — so the frontend's job is only to *ask* the backend, not to *remember* the answer longer than one page load's worth of trust.

## `RequireAuth` renders nothing (not a spinner, not the page) while unauthenticated — the redirect is a side effect, not the render

**Decision:** `frontend/src/components/RequireAuth.tsx` has three branches: `"loading"` → a loading row; `"unauthenticated"` → `return null`, with the actual `router.replace("/login")` call happening in a `useEffect` watching that same status; `"authenticated"` → render the real children.

**Why this specific split, not "redirect inline during render":** calling `router.replace()` directly in the render path is a side effect during render, which React (and Next.js's own rules) disallow doing reliably — it has to happen in an effect, which necessarily runs *after* the render it was triggered by. If that render showed the protected `children` while `status === "unauthenticated"`, there would be one visible frame of a logged-out user seeing a logged-in page's content before the redirect fires. Returning `null` for that status removes that frame entirely — there's nothing to flash, regardless of how fast or slow the effect's `router.replace()` call resolves.

## Registration auto-chains into login, because the backend's `/register` doesn't start a session

**Decision:** `AuthProvider.register()` calls `apiRegister()` then immediately `apiLogin()` with the same credentials, rather than just calling `apiRegister()` and leaving the person on a "registered, now go log in" screen.

**Why:** confirmed by reading `backend/app/api/v1/auth.py`'s `register` route — it creates the `User` row and returns `201`, but never calls `create_session`/sets any cookie. Treating "create an account" as two separate user-facing steps (fill form → separately log in) would be correct but needlessly friction-y for what the backend itself treats as adjacent operations. If the automatic login step fails (e.g. a rate limit happens to trip in that exact window), the account still exists — `register()` surfaces a distinct, honest message ("account was created, please log in") rather than either silently failing or claiming a session that doesn't exist.

## A single `useRedirectOnUnauthorized()` hook, not three separate 401 checks, for session-expires-mid-visit

**Decision:** `frontend/src/lib/auth.tsx` exports `useRedirectOnUnauthorized()`, called from the catch blocks in `leads/page.tsx`, `leads/new/page.tsx`, and `leads/[id]/LeadDetailClient.tsx`. It checks `err instanceof ApiError && err.status === 401`; if so, it flips the shared auth context straight to `"unauthenticated"` (no extra network call — the 401 already told us the session is gone) and calls `router.replace("/login")`, returning `true` so the caller skips setting its own generic error message.

**Why this needed its own mechanism, distinct from `RequireAuth`:** `RequireAuth` only runs its check once, when a protected page is first entered — it has no way to know if the session cookie expires *while the person is still sitting on that page* (e.g. a long-idle tab, then a page interaction). Without this hook, that scenario would have shown a misleading "Failed to load leads" / "Failed to update status" banner instead of correctly recognizing "you're not logged in anymore." Centralizing it in one hook (rather than writing the same `if (err.status === 401)` branch three times slightly differently) means the behavior is identical everywhere it's needed and only has to be gotten right once.

## Frontend test stack: Vitest + React Testing Library, added in two small steps, not all at once

**Decision:** Stage B added only `vitest` (plus a `tinypool` override for a real, verified vulnerability fix — see the npm audit note in `HANDOFF.md`) for plain API-client unit tests. Stage C added `jsdom` and `@testing-library/react` only once component rendering was actually needed. No test-framework dependency was added speculatively ahead of being used.

**Why the `tinypool` override was trusted, not just "it installed":** before keeping it, the exact option names `vitest@2.1.9` passes to `Tinypool`'s constructor (`runtime`, `maxThreads`, `minThreads`, `isolateWorkers`, `concurrentTasksPerWorker`, `terminateTimeout`) were checked against `tinypool@2.2.0`'s own `dist/index.d.ts` — all still present and typed identically — and the full suite was run under *both* of tinypool's runtime backends (`--pool=threads` and the default `forks`) to exercise both code paths, not just the default. This is recorded here because "the install succeeded" was explicitly called out as insufficient evidence earlier in this project, correctly.

**Remaining open npm audit finding, deliberately not force-fixed:** `vitest@2.1.9` (and its `vite@5.4.21`) has one critical finding (`GHSA-5xrq-8626-4rwp`/`GHSA-82fw-gwwq-j7x9`, arbitrary file read "when the Vitest UI server is listening") with no non-major fix available — `vitest@4.1.11+` requires `vite@6.4.3+`, which conflicts with `vitest@2.1.9`'s own `vite: ^5.0.0` dependency declaration. This project's test command (`vitest run`) never starts the UI server the advisory's trigger condition requires, which bounds the real-world risk, but the finding itself remains open in the dependency tree — not suppressed, not worked around with `--force`.

# Repository Agent Instructions

These instructions apply to any coding agent working in this repository
(Claude Code, Codex, or any other tool, in any session). The project
owner is learning as this is built, not just outsourcing it — explain
your reasoning, don't just produce diffs.

## Before doing anything

1. Read `PROJECT_SPEC.md` (which points to `SPEC.md`, the canonical
   specification), `HANDOFF.md` (current verified state), and
   `DECISIONS.md` (why things are the way they are) before any
   significant work.
2. Inspect the current repository and run `git status` before editing
   anything. Do not assume the state described in `HANDOFF.md` is still
   accurate without checking — it is a snapshot, not a live view.
3. Check whether a `.env` file already exists in `backend/` before
   assuming database/credential configuration is missing.

## How to work

- **Work one phase or checkpoint at a time.** Do not jump ahead to a
  later phase (e.g. LangGraph, research agents, RAG) while an earlier
  one is incomplete or unverified. See `SPEC.md` §19 for the phase list.
- **Provide an explicit verification plan and actually run it** before
  reporting a task complete. Never claim a test, migration, or security
  check passed unless you actually ran it and saw the result yourself in
  this session.
- **Make minimal, scoped changes.** Preserve existing working
  functionality. Don't refactor or "clean up" code outside what was
  asked.
- **Never overwrite unrelated user changes.** If a file looks different
  from what you expect (based on `HANDOFF.md` or your own prior edits),
  say so and ask rather than silently reverting or overwriting it.

## Hard constraints

- **Never expose credentials.** Never print `.env` contents, API keys,
  database connection strings, or passwords — not in chat, not in
  tracebacks, not in documentation. Refer to environment variables by
  name only (e.g. `DATABASE_URL`), never by value. If a tool's error
  output would include a secret (e.g. a SQLAlchemy connection error),
  filter or suppress it before showing the result.
- **Never run integration tests against production.** This project uses
  Supabase as the primary database (`DATABASE_URL`) and a separate,
  privilege-restricted `pitchpilot_test_runner` role scoped to a
  `pitchpilot_test` schema for automated tests (`TEST_DATABASE_URL`).
  Tests must only ever connect via `TEST_DATABASE_URL`. See
  `DECISIONS.md` for why this design was chosen and how it's enforced.
- **Do not commit, push, reset, or rewrite Git history without explicit
  approval for that specific action.** A prior approval to commit does
  not carry over to later changes.
- **Do not run destructive database operations** (`DROP SCHEMA`,
  `CASCADE`, truncating/dropping production tables, broad cleanup
  scripts) without explicit, scoped approval. Cleanup in tests must stay
  confined to objects owned by the test suite in `pitchpilot_test`.
- **Stop and report** — rather than improvising a workaround — if you
  encounter: a destructive action, an ambiguous requirement, an
  unexpected database state (schema/data that doesn't match
  `HANDOFF.md`), or a permission/credential blocker. Explain the
  blocker and wait rather than guessing.

## Explaining your work

This is a learning project. When you make a non-trivial decision (a
library choice, a schema design, a security tradeoff), briefly explain
*why*, not just *what*. When you finish a phase or checkpoint, summarize
what changed, how it was verified, and what remains — the project owner
should be able to follow along and build their own understanding of the
system, not just receive a working result they don't understand.

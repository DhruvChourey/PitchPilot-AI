# PitchPilot AI — Project Specification (pointer)

The canonical, complete project specification lives in **[`SPEC.md`](SPEC.md)**
at the repository root. That file was the original specification this
project was built from and remains authoritative — this file intentionally
does not duplicate its content, to avoid the two documents drifting apart.

This pointer file exists so that any coding agent following the
`AGENTS.md` protocol ("read `PROJECT_SPEC.md` before significant work")
has a stable, predictable entry point, even though the historical filename
is `SPEC.md`.

## What's in `SPEC.md`

- Product vision and North Star
- MVP scope (what's required vs. deferred to later phases)
- Recommended technology stack (frontend, backend, orchestration, LLM
  provider abstraction, embeddings/RAG, persistence, document generation)
- High-level architecture diagram and component boundaries
- Agent roles and contracts (Orchestrator, Research, Knowledge/RAG,
  Strategy, Content/Pitch, Critic/Evaluator)
- Shared state schema and goal-alignment rules
- Scope enforcement and guardrails design
- Research/evidence model (verified_fact / inference / hypothesis / unknown)
- RAG and vector database design
- LLM provider abstraction and free-first policy
- The full LangGraph workflow node list
- Pitch deck and deliverables spec
- Database table list, API endpoint list
- Observability, evaluation, security, and reliability requirements
- The phased implementation plan (Phase 0 through Phase 10)
- Coding-agent instructions and the Definition of Done

## Current implementation status relative to the spec

See **[`HANDOFF.md`](HANDOFF.md)** for the up-to-date, verified state of
what is actually built (as opposed to what the spec describes as the
eventual direction). As of this writing, the repository has completed
spec Phase 0 (environment/health) and Phase 1 (lead management CRUD on
PostgreSQL/Supabase) only. LangGraph, the research agent, RAG/embeddings,
and pitch generation described in `SPEC.md` are **not yet implemented** —
do not assume otherwise without checking the actual code.

See **[`DECISIONS.md`](DECISIONS.md)** for architecture/security decisions
made while implementing the spec (e.g. Supabase as the hosted Postgres
choice, the dedicated-test-schema design) that aren't captured in the
original specification document itself.

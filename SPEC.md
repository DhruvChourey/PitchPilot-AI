# PitchPilot AI --- Complete Project Specification

> **Project type:** Learning-first Agentic AI / Generative AI
> application\
> **Primary outcome:** Turn a business lead into evidence-backed company
> research, a personalized sales strategy, an editable pitch deck, and a
> complete outreach kit.\
> **Cost constraint:** Start with a zero-mandatory-cost, local-first
> setup. Do not require paid APIs, paid hosting, or paid databases for
> local development. Free hosted API tiers may be optional and must be
> replaceable.

------------------------------------------------------------------------

## 1. Product Vision

PitchPilot AI is an agentic sales-intelligence platform. A user submits
a company name, website, public profile URL, lead notes, and their own
services. The system researches the company, identifies plausible
opportunities supported by evidence, maps those opportunities to the
user's actual capabilities, and generates tailored sales collateral.

This is also a learning project. The implementation must help the
developer understand LLMs, prompting, structured outputs, tool calling,
embeddings, RAG, vector databases, agent orchestration, guardrails,
evaluation, and production engineering. Do not generate the entire
codebase in one pass. Implement in phases, explain important decisions,
and test each phase.

### North Star

> Research the given prospect, identify evidence-backed business
> opportunities that match the user's real services, and produce an
> accurate, persuasive, personalized sales pitch.

Every agent action should contribute to this goal. The system should
avoid irrelevant research, disclose missing evidence, and never invent
facts to make a pitch sound stronger.

### Core principles

1.  Evidence before persuasion.
2.  A controlled workflow before a multi-agent swarm.
3.  Local-first and free-by-default during development.
4.  Structured state and outputs rather than unstructured agent-to-agent
    chat.
5.  Scope enforcement and backend permissions, not prompt-only security.
6.  Bounded retries, budgets, timeouts, and explicit completion
    criteria.
7.  Human approval before external side effects such as sending
    outreach.
8.  Learnable, modular code with tests and explanations.

------------------------------------------------------------------------

## 2. Primary User Journey

1.  User configures their organization, services, value propositions,
    pricing rules, approved case studies, brand style, and contact
    details.
2.  User creates a lead with a company name and/or website, optional
    contact role, public profile URL, lead notes, and desired outcome.
3.  User starts a research run.
4.  The system creates a persistent run record and initializes workflow
    state.
5.  Research tools discover or fetch publicly accessible pages and
    extract relevant evidence.
6.  The knowledge retrieval layer finds relevant approved agency
    materials and prior research.
7.  The strategy stage identifies and ranks potential opportunities,
    explicitly distinguishing facts from hypotheses.
8.  The user can review and edit the proposed strategy.
9.  The content stage produces a slide outline and supporting sales
    collateral.
10. The renderer generates editable PPTX and document files.
11. Deterministic validators and an evaluator check source traceability,
    scope, output schemas, and file integrity.
12. Failed checks trigger bounded, targeted revisions.
13. The user reviews, edits, approves, and downloads deliverables.
14. The run, evidence, evaluations, and artifact versions remain
    available for future follow-up.

------------------------------------------------------------------------

## 3. MVP Scope

### Required for MVP

-   Lead creation and editing.
-   Organization/service profile configuration.
-   Public website research using supplied URLs and available search
    tooling.
-   Source URL, title, retrieval time, and publication date where
    available.
-   Findings categorized as verified facts, inferences, hypotheses, or
    unknowns.
-   Evidence-backed opportunity analysis and service matching.
-   Research report with citations.
-   Editable slide outline.
-   Editable PowerPoint (`.pptx`) generation.
-   Personalized introductory email, LinkedIn message, discovery
    questions, and follow-up draft.
-   Local persistence for leads, runs, evidence, strategies,
    evaluations, and artifact metadata.
-   Scope classification and tool authorization.
-   Critic/evaluation stage with bounded revisions.
-   Clear errors, retries, and truthful progress reporting.
-   Tests and setup documentation.

### Later phases, not MVP blockers

-   Bulk CSV lead upload.
-   CRM integrations.
-   Automated email sending.
-   Scheduled follow-up monitoring.
-   Team accounts and multi-tenant production deployment.
-   Advanced hybrid search/reranking.
-   Dedicated vector database service.
-   Autonomous outbound sales.
-   Billing and analytics dashboards.

Do not implement these early unless the MVP is stable and tests show a
clear need.

------------------------------------------------------------------------

## 4. Recommended Technology Stack

### Frontend

-   Next.js
-   TypeScript
-   Tailwind CSS
-   A consistent accessible component system
-   Server-side calls to the backend; never expose provider secrets in
    browser code

Responsibilities: - Dashboard and recent leads - Lead intake/edit form -
Run progress and event timeline - Research report and source viewer -
Opportunity/strategy review - Pitch outline and deck preview - Artifact
downloads - Organization, service, brand, model-provider, and local
configuration screens

### Backend

-   Python
-   FastAPI
-   Pydantic for validated inputs and structured outputs
-   SQLAlchemy or a similarly maintainable database layer
-   Database migrations
-   HTTPX for HTTP requests
-   Beautiful Soup for HTML extraction

### Agent orchestration

-   LangGraph for explicit stateful workflow orchestration
-   Typed state
-   Conditional routing
-   Checkpointing
-   Bounded retries and revision loops
-   Human approval gates where required

Use one orchestrator and a small number of specialized nodes first. An
agent role does not have to be a separate process or independently
running model.

### LLM provider abstraction

Support interchangeable providers through a common adapter:

-   Gemini API, if a free tier is available to the user's account
-   Groq API, if a free tier is available to the user's account
-   Ollama for local inference
-   Additional providers only through the same adapter interface

Free-tier access, model availability, and quotas may change. The
application must not assume unlimited hosted inference. Provider
failures should result in a clear pause, a supported fallback, or a
local-model option---not endless retries.

### Embeddings and RAG

-   Sentence Transformers or another suitable local embedding model
-   PostgreSQL with pgvector
-   Local embedding generation by default
-   Document ingestion, chunking, metadata filtering, retrieval, and
    source traceability

### Persistence and files

-   PostgreSQL + pgvector for the recommended architecture
-   Local file storage for development artifacts
-   Keep binary files outside the database where practical; store
    metadata and paths/keys in the database
-   Use a persistent LangGraph checkpoint mechanism compatible with the
    selected database setup

### Document generation

-   `python-pptx` for editable PowerPoint
-   `python-docx` for Word proposals
-   Optional PDF export using a suitable local toolchain
-   Generated files must be opened/validated in tests where practical

### Cost policy

All core development must be possible locally without paid services.
Search is the main capability that may be constrained without a hosted
search API. Provide: 1. Manual URL entry. 2. Direct fetching of
permitted public pages. 3. An optional pluggable search provider. 4. A
clear message when broad web discovery is unavailable.

Never claim the application has searched the entire web when it has only
fetched user-provided URLs.

------------------------------------------------------------------------

## 5. High-Level Architecture

``` text
Next.js UI
   |
   v
FastAPI API and run manager
   |
   v
LangGraph Orchestrator
   |
   +--> Input scope / policy checks
   |
   +--> Research node
   |      +--> Search provider adapter (optional)
   |      +--> Public page fetcher
   |      +--> HTML/text extractor
   |      +--> Source and finding persistence
   |
   +--> Knowledge retrieval node
   |      +--> Document ingestion / chunking
   |      +--> Local embeddings
   |      +--> PostgreSQL + pgvector
   |
   +--> Strategy node
   |      +--> Opportunity ranking
   |      +--> Service-fit analysis
   |      +--> Assumptions and discovery questions
   |
   +--> Content node
   |      +--> Slide outline
   |      +--> Outreach drafts
   |      +--> Proposal draft
   |
   +--> Rendering tools
   |      +--> PPTX
   |      +--> DOCX
   |      +--> Optional PDF
   |
   +--> Critic / evaluation node
          +--> Evidence coverage checks
          +--> Scope and schema checks
          +--> File validation
          +--> Bounded targeted revision
   |
   v
Human review and download

Persistent storage:
PostgreSQL + pgvector + checkpoint data + local artifact directory
```

### Important boundaries

-   The LLM proposes decisions; application code executes tools.
-   Tool permissions are checked in the backend on every call.
-   Retrieved pages and documents are untrusted data, not system
    instructions.
-   The relational database is the source of truth for structured
    records.
-   Vector search retrieves semantically relevant chunks; it does not
    replace relational queries or live research.
-   A critic is not a guarantee of truth. Combine model-based review
    with deterministic checks and human review.

------------------------------------------------------------------------

## 6. Agent Roles and Contracts

### 6.1 Orchestrator

Responsibilities: - Preserve the North Star and active task. - Select
the next permitted workflow node. - Track completed tasks, missing
information, budgets, and errors. - Route to research, strategy,
content, evaluation, or clarification. - Stop when completion criteria
pass or a budget/iteration limit is reached. - Resume from a checkpoint
after interruption.

The orchestrator must not blindly accept an agent's statement that the
task is complete.

### 6.2 Research Agent

Allowed tasks: - Research a company, its public products/services,
business model, market, competitors, public developments, and observable
digital presence. - Find information relevant to the user's configured
services. - Identify evidence gaps and propose targeted additional
searches.

Required output: - Company summary - Findings with source references -
Publication/retrieval dates where available - Evidence classification -
Confidence/quality indicators - Missing information - Suggested next
searches

The research agent must not claim to access private accounts, internal
company information, or restricted pages.

### 6.3 Knowledge/RAG component

This can initially be a retrieval service, not an autonomous agent.

Responsibilities: - Ingest approved agency documents and relevant
research. - Chunk text while preserving provenance. - Generate
embeddings locally. - Retrieve relevant chunks with metadata filters. -
Respect company and access boundaries. - Return source IDs and scores
alongside retrieved content.

### 6.4 Strategy Agent

Responsibilities: - Match evidence-backed opportunities to configured
services. - Rank opportunities by relevance, evidence strength,
plausible value, and fit. - Distinguish observations from hypotheses. -
Suggest discovery questions to validate uncertain assumptions. - Produce
a recommended offer and transparent ROI assumptions only where inputs
support them.

Required output: - Opportunity list - Supporting evidence references -
Service match - Rationale and confidence - Expected value with
assumptions - Missing inputs - Discovery questions - Recommended next
step

### 6.5 Content/Pitch Agent

Responsibilities: - Turn the approved strategy into a slide outline. -
Generate concise, prospect-specific slide content. - Draft emails,
LinkedIn messages, call scripts, and proposals. - Use only configured
services, approved case studies, and verified results. - Preserve
references for claims that require evidence.

The content agent must not invent pricing, testimonials, customer
outcomes, partnerships, company facts, or guaranteed ROI.

### 6.6 Critic/Evaluator

Responsibilities: - Identify unsupported claims and missing citations. -
Check alignment between prospect, service, strategy, and content. -
Check required sections and schema correctness. - Report specific
failures and targeted revision instructions. - Avoid vague scores
without explanations.

Use deterministic validators for machine-checkable rules. Use model
evaluation for qualitative issues such as relevance and clarity, then
calibrate it against human-reviewed examples.

------------------------------------------------------------------------

## 7. Goal Alignment and Shared State

The workflow must maintain explicit state. Do not rely on the model's
conversational memory alone.

Example initial state (illustrative, not a complete production schema):

``` python
from typing import TypedDict, Any

class AgentState(TypedDict, total=False):
    run_id: str
    lead_id: str
    company_id: str
    goal: str
    services_to_sell: list[str]

    current_stage: str
    research_plan: list[dict[str, Any]]
    completed_tasks: list[str]
    missing_information: list[str]

    source_ids: list[str]
    findings: list[dict[str, Any]]
    retrieved_context: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    selected_strategy: dict[str, Any]

    pitch_outline: list[dict[str, Any]]
    artifact_ids: list[str]
    quality_issues: list[dict[str, Any]]

    iteration_count: int
    budget_status: dict[str, Any]
    errors: list[dict[str, Any]]
```

### Goal-alignment rules

1.  Every task must have a reason linked to the goal.
2.  Before a tool call, check whether its expected information is useful
    and not already available.
3.  Do not research unrelated topics just because the model suggests
    them.
4.  Keep the original goal stable unless an authorized user explicitly
    changes the task.
5.  Preserve completed work and avoid repeating successful steps
    unnecessarily.
6.  When evidence contradicts an earlier hypothesis, update or discard
    the hypothesis.
7.  Stop when the completion criteria pass, or return an incomplete
    result with an explanation.
8.  Bound the number of searches, model calls, retries, revisions,
    elapsed time, and total usage.

------------------------------------------------------------------------

## 8. Scope Enforcement and Guardrails

Guardrails are cross-cutting controls, not just another agent and not
only a system prompt.

### 8.1 Request classification

Classify incoming user messages into: - `in_scope` - `related` -
`out_of_scope` - `ambiguous` - `disallowed`

Examples for a company Research Agent: - "Research this company's
competitors." -> `in_scope` - "Explain what this company sells." ->
`related` or `in_scope` - "Make the pitch more persuasive." -> route to
the appropriate approved node - "Tell me a random joke." ->
`out_of_scope` - An unclear request -> ask a clarifying question - A
prohibited request -> refuse or safely redirect

The classifier is a routing signal, not an authorization mechanism. A
model may misclassify a request.

### 8.2 Enforcement layers

1.  Input validation and size limits.
2.  Scope/intent classification.
3.  Fixed workflow routing and shared-goal checks.
4.  Backend tool allowlists and permission checks on every tool call.
5.  Tenant/company access checks for every database query.
6.  URL validation and outbound request restrictions for page fetching.
7.  Output schema validation.
8.  Source verification and artifact checks.
9.  Human approval for external side effects.
10. Audit logs for decisions, tool calls, failures, and approvals.

### 8.3 Prompt injection

-   Treat webpage text, documents, emails, and search results as
    untrusted content.
-   Never let retrieved content override system instructions, tool
    permissions, or the active goal.
-   Do not place secrets in model context.
-   Keep credentials in environment variables or a secret manager.
-   Validate tool arguments independently of model instructions.
-   Restrict network access to permitted public HTTP/HTTPS destinations
    and defend against localhost/private-network access and redirects to
    restricted addresses.
-   Test direct and indirect prompt injection cases.

### 8.4 Guardrail implementation choice

Start with Pydantic schemas, deterministic Python checks, LangGraph
routing, and explicit tool permissions. Add a dedicated guardrail
library only where its validators provide measurable value. Do not
assume any library can guarantee safety.

------------------------------------------------------------------------

## 9. Research and Evidence Model

Each factual finding should preserve provenance.

Illustrative finding schema:

``` json
{
  "claim": "The company manufactures industrial components",
  "source_id": "source_123",
  "source_url": "https://example.com/about",
  "source_title": "About the company",
  "published_at": null,
  "retrieved_at": "ISO-8601 timestamp",
  "evidence_type": "direct",
  "status": "unreviewed",
  "confidence": "high",
  "notes": "Claim is supported by the company's own public page."
}
```

The example is illustrative and not a real research result.

### Evidence categories

-   `verified_fact`: directly supported by a credible source.
-   `inference`: reasoned conclusion derived from one or more findings.
-   `hypothesis`: plausible possibility requiring validation.
-   `unknown`: information not established by available evidence.
-   `contradicted`: sources conflict or the claim is not supported.

Do not use confidence labels as a substitute for citations. Track the
source and explain why it supports the claim.

### Source handling

-   Record the URL, title, source type, retrieval time, and publication
    date where available.
-   Deduplicate URLs and near-duplicate content.
-   Preserve enough extracted text or a stable content snapshot for
    audit, subject to legal and site restrictions.
-   Clearly distinguish the date a page was retrieved from the date an
    event occurred.
-   Recheck time-sensitive claims before final output when practical.
-   Do not claim a source says something it does not say.

------------------------------------------------------------------------

## 10. RAG and Vector Database Design

Use PostgreSQL for structured data and pgvector for semantic search in
the initial architecture.

### What belongs in vector retrieval

-   Approved agency service descriptions
-   Approved case studies and verified results
-   Sales playbooks and objection-handling guidance
-   Relevant chunks of public company research
-   Prior research that is appropriate to reuse

### What should remain relational

-   Company names and identifiers
-   Lead contact fields and statuses
-   Prices and commercial terms
-   Run states and timestamps
-   Source metadata and verification status
-   Artifact locations and permissions
-   Approval records

### Ingestion pipeline

1.  Accept an approved file or extracted public page.
2.  Extract text.
3.  Clean content without losing source identity.
4.  Split into useful chunks.
5.  Attach metadata: `company_id`, `document_id`, `document_type`,
    `source_url`, `source_date`, `verification_status`, `access_scope`.
6.  Generate embeddings locally.
7.  Store chunks and vectors.
8.  Retrieve with similarity search plus metadata filters.
9.  Return chunk text, metadata, source ID, and similarity score.
10. Evaluate retrieval quality against a small test set.

### Memory types

-   Working memory: current workflow state.
-   Episodic memory: prior runs, decisions, and outcomes stored
    relationally.
-   Semantic memory: embedded document chunks.
-   User/business configuration: services, pricing rules, tone, and
    approved case studies stored as structured records.

Do not automatically promote generated hypotheses or unreviewed outputs
to trusted knowledge. Keep company-specific information isolated and
filter every retrieval by access scope.

------------------------------------------------------------------------

## 11. LLM Provider Abstraction and Free-First Policy

Create a common provider interface so agents do not depend directly on
one vendor.

Suggested methods: - `generate_text(...)` - `generate_structured(...)` -
`supports_tools(...)` - `record_usage(...)` -
`handle_provider_error(...)`

### Provider behavior

-   Configure provider/model through environment variables and settings.
-   Validate model capabilities, including structured outputs and tool
    calling.
-   Track request count, latency, token usage when reported, and
    provider errors.
-   Respect provider rate limits.
-   Use bounded backoff for transient errors.
-   On quota exhaustion, pause, switch to a configured compatible
    provider, or ask the user to continue later.
-   Do not silently change model behavior without recording the
    provider/model used.
-   Do not assume consumer chat credits apply to API usage.
-   Check current terms and free-tier limits before relying on hosted
    providers.
-   Avoid sending sensitive or confidential lead data to a hosted
    provider without reviewing its data-use policy.

Local Ollama inference can reduce hosted inference costs but still
requires suitable hardware, disk, electricity, and time.

------------------------------------------------------------------------

## 12. LangGraph Workflow

Recommended graph nodes:

1.  `validate_request`
2.  `classify_scope`
3.  `initialize_run`
4.  `load_business_context`
5.  `plan_research`
6.  `research_company`
7.  `extract_and_store_evidence`
8.  `retrieve_knowledge`
9.  `evaluate_research_sufficiency`
10. `analyze_opportunities`
11. `approve_or_edit_strategy` (human checkpoint where configured)
12. `create_pitch_outline`
13. `generate_sales_collateral`
14. `render_artifacts`
15. `validate_claims_and_files`
16. `revise_failed_sections`
17. `save_final_results`
18. `await_human_review`
19. `finish_or_report_incomplete`

### Routing examples

-   Off-topic -> polite redirect; preserve active run.
-   Ambiguous -> ask clarification.
-   Missing research -> targeted additional search if budget remains.
-   Research budget exhausted -> return partial results with gaps.
-   Strategy rejected by user -> regenerate strategy, not all research.
-   Unsupported claim -> revise the affected content.
-   Invalid file -> retry rendering within limits.
-   Quota failure -> pause or use an explicitly configured fallback.
-   Passing checks -> save final artifacts and request review.

### Checkpointing

Persist enough state to resume after process restarts. Test interruption
and resumption. Checkpoint storage and artifact storage must not assume
the process remains alive in memory.

------------------------------------------------------------------------

## 13. Pitch Deck and Sales Deliverables

### Default deck outline

Adapt the deck to the lead and service; do not force irrelevant slides
into every presentation.

1.  Personalized cover
2.  Executive summary
3.  Company context
4.  Relevant market or business developments
5.  Evidence-backed opportunity
6.  Proposed solution
7.  Solution workflow or architecture
8.  Implementation roadmap
9.  Expected impact and transparent ROI assumptions
10. Investment/package options, only when configured pricing exists
11. Relevant capabilities and verified case studies
12. Next steps and call to action

### Presentation quality

-   Consistent theme, typography, and spacing.
-   Concise slide copy.
-   Visual hierarchy, diagrams, timelines, and charts when useful.
-   Editable text and shapes.
-   Source notes for factual claims.
-   No fake logos, testimonials, or customer results.
-   No invented pricing.
-   Detect missing content and layout overflow where feasible.
-   Save versions when regenerating.
-   Provide a preview and allow targeted slide regeneration.

### Other deliverables

-   Company research brief
-   Opportunity analysis
-   Personalized introductory email
-   LinkedIn outreach draft
-   Discovery-call questions and agenda
-   Presenter notes or meeting script
-   Objection-handling guide
-   Follow-up email drafts
-   Proposal document
-   Internal lead briefing

All outreach must remain draft-only until the user explicitly approves
any sending integration.

------------------------------------------------------------------------

## 14. Database Tables

Create migrations for tables such as:

| Table | Purpose |
| --- | --- |
| `organizations` | User's organization and configuration |
| `service_offerings` | Services, capabilities, prices/rules, and eligibility |
| `case_studies` | Approved case studies and verified results |
| `companies` | Company identity and public website |
| `leads` | Contact details, notes, status, company association |
| `research_runs` | Run status, timestamps, model/provider usage, errors |
| `sources` | Source URLs, title, publication/retrieval timestamps |
| `findings` | Claims, evidence classification, source relationships |
| `documents` | Source and uploaded document metadata |
| `document_chunks` | Chunk text, embedding, provenance and filters |
| `strategies` | Ranked opportunities and selected approach |
| `agent_events` | Tool calls, node transitions, retries and errors |
| `evaluations` | Scores, failed checks, explanations and revisions |
| `artifacts` | Generated file metadata, versions, paths and checksums |
| `approvals` | Human review and approval decisions |

Add foreign keys, indexes, constraints, migrations, and access checks.
If multi-user support is added, enforce organization boundaries at the
backend and database layer.

------------------------------------------------------------------------

## 15. API Endpoints

Example initial API surface:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Backend health |
| `GET` | `/leads` | List leads |
| `POST` | `/leads` | Create lead |
| `GET` | `/leads/{lead_id}` | Retrieve lead |
| `PATCH` | `/leads/{lead_id}` | Update lead |
| `POST` | `/leads/{lead_id}/research-runs` | Start a run |
| `GET` | `/runs/{run_id}` | Get status and summary |
| `GET` | `/runs/{run_id}/events` | Read run events |
| `POST` | `/runs/{run_id}/cancel` | Request cancellation |
| `GET` | `/runs/{run_id}/findings` | Retrieve evidence-backed findings |
| `GET` | `/runs/{run_id}/strategy` | Retrieve strategy |
| `PATCH` | `/runs/{run_id}/strategy` | Edit/approve strategy |
| `POST` | `/runs/{run_id}/generate` | Generate artifacts |
| `GET` | `/artifacts/{artifact_id}` | Retrieve artifact metadata |
| `GET` | `/artifacts/{artifact_id}/download` | Download authorized artifact |

Validate all IDs, inputs, permissions, URLs, and file paths. Do not
allow user-supplied paths to read arbitrary files. Use appropriate
authentication before exposing the app beyond localhost.

------------------------------------------------------------------------

## 16. Observability and Evaluation

Record: - Run ID and lead ID - Current graph node and transitions - Tool
name and sanitized arguments - Tool result status and duration -
Model/provider/model version when available - Usage/cost metadata when
available - Retry count and reason - Evidence IDs used in decisions -
Evaluator results and revision history - Artifact version and validation
result

Never log API secrets. Redact sensitive fields and avoid unnecessary
storage of personal information.

### Evaluation dataset

Build a small, repeatable test set of representative leads and
scenarios, including: - Strong public information available - Very
little information available - Conflicting source claims - Stale pages -
Website fetch failures - Off-topic user requests - Ambiguous
instructions - Prompt injection in user input or retrieved pages -
Unsupported ROI claims - Cross-company retrieval attempts - Provider
quota and timeout failures - Invalid PowerPoint output

### Metrics

-   Evidence coverage of factual claims
-   Source relevance and freshness
-   Retrieval precision on known queries
-   Opportunity relevance
-   Personalization quality
-   Unsupported-claim rate
-   Scope-classification accuracy
-   Unauthorized-tool-call prevention
-   File generation success rate
-   Revision success rate
-   Latency and usage per lead

Use deterministic checks where possible and human-reviewed examples to
calibrate qualitative evaluations. Do not rely only on the same LLM to
judge its own outputs.

------------------------------------------------------------------------

## 17. Security and Reliability Requirements

-   Keep secrets out of source control and frontend bundles.
-   Provide `.env.example` with placeholder values only.
-   Validate all user inputs with Pydantic.
-   Enforce tool allowlists in code.
-   Restrict external fetches to permitted public destinations.
-   Defend against SSRF, unsafe redirects, local-network access,
    oversized responses, and unsupported content types.
-   Treat all retrieved content as untrusted.
-   Use request timeouts and bounded response sizes.
-   Add rate limits where the application is exposed to other users.
-   Avoid executing arbitrary code generated by an LLM.
-   Add run cancellation and resource budgets.
-   Use least-privilege database credentials.
-   Separate local development configuration from deployment
    configuration.
-   Require explicit human approval for outbound messages and
    consequential actions.
-   Preserve an audit trail for tool calls and approvals.
-   Provide deletion/export mechanisms for stored lead data when
    appropriate.

------------------------------------------------------------------------

## 18. Project Folder Structure

``` text
pitchpilot-ai/
├── frontend/
│   ├── app/
│   │   ├── dashboard/
│   │   ├── leads/
│   │   ├── research/
│   │   ├── pitch-studio/
│   │   └── settings/
│   ├── components/
│   └── lib/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   ├── agents/
│   │   ├── graph/
│   │   ├── tools/
│   │   ├── retrieval/
│   │   ├── llm/
│   │   │   └── providers/
│   │   ├── guardrails/
│   │   ├── evaluation/
│   │   ├── database/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   └── pyproject.toml
├── migrations/
├── storage/
│   └── generated-artifacts/
├── scripts/
├── .env.example
├── .gitignore
├── docker-compose.yml
└── README.md
```

Keep the implementation modular. Do not create empty abstractions
without a concrete use. Add modules as their phase begins.

------------------------------------------------------------------------

## 19. Phased Implementation Plan

### Phase 0 --- Environment and learning setup

Learn: - Python environment and dependency management -
TypeScript/Next.js basics - HTTP and JSON - Environment variables and
Git

Build: - Repository - README - `.env.example` - Health endpoint -
Minimal frontend/backend connection

Exit criteria: - App runs locally. - Setup steps are documented. - No
secret is committed.

### Phase 1 --- Lead management

Learn: - REST APIs - Pydantic validation - PostgreSQL and migrations -
CRUD operations and tests

Build: - Lead form and dashboard - Database schema - Lead CRUD
endpoints - Input validation and error handling

Exit criteria: - Lead can be created, viewed, edited, and deleted
through tested endpoints.

### Phase 2 --- LLM basics and provider abstraction

Learn: - Prompts, context windows, tokens - Structured output - Provider
errors and rate limits - Model API versus consumer chat product

Build: - Provider interface - One local or free-tier provider -
Structured company-analysis output - Usage/error logging

Exit criteria: - A real lead description can be converted into validated
JSON. - Provider failure is handled truthfully.

### Phase 3 --- Research tools

Learn: - Tool calling - HTTP requests - HTML extraction - Evidence and
citations - Prompt injection basics

Build: - Public-page fetcher - Optional search adapter - Source and
finding persistence - Research report

Exit criteria: - Every major finding has provenance or is labeled as an
inference/hypothesis. - Fetch failures are reported instead of
fabricated.

### Phase 4 --- Embeddings and RAG

Learn: - Chunking - Embeddings - Cosine similarity or appropriate vector
distance - Metadata filtering - Retrieval evaluation

Build: - Local embedding pipeline - pgvector schema and index - Agency
knowledge ingestion - Filtered retrieval - Small retrieval test set

Exit criteria: - A query retrieves relevant chunks and preserves source
references. - Retrieval does not cross company/access boundaries.

### Phase 5 --- LangGraph and goal-directed workflow

Learn: - Shared state - Nodes and edges - Conditional routing -
Checkpointing - Bounded loops

Build: - Research planning node - Research execution node - Sufficiency
decision - Strategy node - Completion criteria and run status

Exit criteria: - Workflow can choose a targeted next step, stop when
done, and report incomplete research. - Interruption/resumption is
tested.

### Phase 6 --- Scope enforcement and guardrails

Learn: - Input/output validation - Intent classification - Tool
permissions - Prompt injection - Human approval

Build: - Scope classifier - Polite off-topic redirection - Per-agent
tool allowlists - Tool executor checks - Output validation - Adversarial
tests

Exit criteria: - Unrelated requests are redirected. - Unauthorized tools
are blocked in backend code even if a model requests them.

### Phase 7 --- Strategy and sales content

Learn: - Structured generation - Evidence-grounded reasoning -
Evaluation and critic loops - Revision strategies

Build: - Opportunity ranking - Service-fit analysis - Strategy review
screen - Slide outline - Emails and discovery questions

Exit criteria: - Strategy maps to actual services and includes evidence,
assumptions, and questions for validation.

### Phase 8 --- PowerPoint and document generation

Learn: - Document layout - PPTX generation - File validation - Rendering
and visual review

Build: - Reusable slide templates - PPTX renderer - DOCX proposal
renderer - Artifact versioning - Downloads and preview

Exit criteria: - Generated files open successfully, remain editable, and
pass content/layout checks.

### Phase 9 --- Critic and quality evaluation

Learn: - Evaluation datasets - Deterministic checks versus LLM judges -
Failure analysis - Regression tests

Build: - Evidence coverage checker - Required-slide validator -
File-integrity checks - Targeted revision loop - Run quality summary

Exit criteria: - Failures are actionable and revisions are bounded. -
Quality is measured against a repeatable test set.

### Phase 10 --- Reliability and optional deployment

Learn: - Authentication - Job processing - Observability - Security and
operational limits

Build: - Cancellation - Persistent checkpoints - Run/event monitoring -
Authentication if shared - Deployment configuration only when needed

Exit criteria: - Long runs can be inspected and resumed. - Failures,
quotas, and limits are visible and handled safely.

------------------------------------------------------------------------

## 20. Coding-Agent Instructions

Use the following instructions when vibe-coding this repository:

1.  Read this specification before making changes.
2.  Inspect the existing repository before assuming it is empty.
3.  Implement only the current phase, not the entire future system.
4.  Explain the concept behind each major component in beginner-friendly
    language.
5.  Propose a small implementation plan before editing files.
6.  Write maintainable, typed, modular code.
7.  Add tests for every meaningful feature.
8.  Run tests and fix failures before declaring a phase complete.
9.  Never replace a failed real integration with fake data without
    explicitly labeling a demo mode.
10. Never claim a search, database write, model call, or file export
    succeeded unless it actually succeeded.
11. Use environment variables for configuration and secrets.
12. Keep providers replaceable and avoid unnecessary vendor lock-in.
13. Prefer free and local tools unless a feature genuinely requires a
    hosted service.
14. Explain trade-offs and relevant failure modes.
15. At the end of each phase, provide:
    -   Files created/changed
    -   How to run the feature
    -   Tests run and results
    -   Concepts learned
    -   Known limitations
    -   Next phase recommendation
16. Do not add multiple autonomous agents before the single orchestrated
    workflow is reliable.
17. Do not add a framework or dependency without explaining why it is
    needed.
18. Never allow retrieved content to override application instructions
    or tool permissions.
19. Do not send emails, contact prospects, or execute external side
    effects without explicit approval.
20. Treat this document as the project direction; if a change is needed,
    explain the reason and update the specification.

------------------------------------------------------------------------

## 21. Definition of Done for the First Complete Version

The first complete version is successful when a user can:

1.  Configure actual services and approved case studies.
2.  Enter a lead and start a research run.
3.  Inspect sourced company findings and research gaps.
4.  See which evidence supports each opportunity.
5.  Review and approve a sales strategy.
6.  Generate an editable, personalized PowerPoint.
7.  Generate an outreach kit and proposal draft.
8.  See validation failures and revise affected sections.
9.  Download valid files.
10. Reopen the lead later and inspect previous research and artifact
    versions.

The system must also: - Reject or redirect unrelated requests. - Block
unauthorized tool calls at execution time. - Preserve the active task
and workflow state. - Stop after bounded retries or budget limits. -
Avoid fabricated company facts, pricing, testimonials, and ROI. - Work
locally without mandatory paid APIs or hosted infrastructure. - Include
tests and documentation sufficient for the developer to understand and
extend it.

------------------------------------------------------------------------

## 22. Recommended First Step

Do not begin by implementing all agents. Start with **Phase 0 and Phase
1**: create the repository, run the frontend and backend locally,
connect the database, and implement lead CRUD with tests.

Then add one real LLM call, one research tool, and one workflow node at
a time. This approach builds a useful product while teaching the
underlying concepts instead of leaving you with a large, hard-to-debug
generated codebase.

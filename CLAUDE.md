# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

Install dependencies and start the backend:

```bash
pip install -r requirements.txt
python main.py
```

The API runs at `http://0.0.0.0:8000`. Open `dashboard.html` directly in a browser — it is a static file, not served by FastAPI, and hardcodes `http://127.0.0.1:8000` as its backend URL.

There are no tests, no linting configuration, and no build step yet. Once the governance kernel is scaffolded (see Production Roadmap below), run tests with:

```bash
pytest tests/test_policy_kernel.py
python tests/run_validation.py   # aggregate: 38 checks, 7 unit tests
```

## Architecture

This is a two-file full-stack MVP:

- **`main.py`** — FastAPI backend with three endpoints, all returning hardcoded JSON:
  - `GET /` — health/identity check
  - `POST /deploy` — returns simulated multi-agent deployment status and revenue projection
  - `GET /revenue` — returns revenue projection and an `SVY` metric (currently `4.2`)

- **`dashboard.html`** — Standalone static HTML (Tailwind CSS via CDN, vanilla JS `fetch`) with two buttons that call `/deploy` and `/revenue` and display the raw JSON in `<pre>` blocks.

### Domain model (Aethon Standard)

SwarmForge Pro implements the **First-Principles / High-Heavy Weighted Autonomous Systems** framework. The four agents correspond to the four Core Engines:

| Agent key    | Agent type    | Core Engine          | Purpose                          |
|--------------|---------------|----------------------|----------------------------------|
| `developer`  | NeuroSymbolic | AI Sustainment       | Infrastructure & compute uptime  |
| `marketer`   | Causal        | Digital Asset Engine | Content & IP creation / scaling  |
| `analyst`    | Quantum       | Capital Engine       | Yield generation & liquidity     |
| `compliance` | Formal        | Coordination Engine  | Governance & profit distribution |

**Design axioms driving future development:**
- **Autonomous Primacy** — zero human intervention post-initialization
- **Capital Weighting** — resource allocation follows a 50/30/15/5 risk/reward formula
- **Recursive Optimization** — system output (capital, data, assets) feeds back into model improvement
- **Resilience through Redundancy** — multi-agent critics and fail-safes over peak efficiency

**20 Architectural Angles** are grouped in four layers:
- Angles 1–5: Base layer (Liquidity, Content, Logic)
- Angles 6–10: Growth layer (Scaling, Marketing, Partnerships)
- Angles 11–15: Security layer (Audits, Legal, Insurance) — Angle 14 is the mandatory Insurance buffer
- Angles 16–20: Meta layer (Self-healing, R&D, Evolution) — Angle 17 is the Red Team audit gate

All agent state and revenue figures (`$3790/month`, SVY `4.2`) are currently hardcoded stubs. The intended path is: prove ROI at the single-transaction/content-piece level first, then scale (First Principles Deployment).

## Prompting Patterns for Agent Development

When implementing real agent logic (replacing the hardcoded stubs), use these patterns:

**Defining an agent's system prompt** (use for each of the four engines):
```
You are <engine name>, a <role> in the SwarmForge autonomous system.

GOAL
<primary job in one sentence>

BEHAVIOR
- Always: ...
- Never: ...

CONSTRAINTS
- Use only verified data; never invent values.
- If uncertain, surface the uncertainty rather than guessing.

OUTPUT
- Return structured JSON matching the existing /deploy schema.
```

**Orchestrating multi-step agent tasks** (5.12 pattern):
```
GOAL: <outcome with definition of done>
CONTEXT: <relevant state, prior agent outputs>
CONSTRAINTS: <what not to touch, capital limits, compliance rules>
PROCESS: Work step by step. After each step, state what you did and what's next.
WHEN UNSURE: Ask before any irreversible action.
DONE WHEN: <verifiable condition — e.g., SVY >= 4.5 and revenue >= $3790>
```

**Context engineering rules** that apply to this project:
- Pass prior agent outputs as structured context, not raw conversation history — prevents context drift in long autonomous runs.
- Always label source data with XML tags (`<capital_state>`, `<market_data>`) and reference those tags in instructions.
- For the Coordination Engine (compliance agent), require quote extraction before analysis: "Extract the exact rule/clause that applies, then reason from it."
- When chaining agents (Capital → Digital Asset → Coordination → AI Sustainment), compact intermediate outputs into a brief (decisions made, constraints, open items) before passing to the next agent.

## Production Roadmap

**Current state: PRL-2 — Governance Kernel Prototype Validated.** The codebase is a validated stub. The architecture has been fully specified and its governance kernel tested externally; those artifacts now need to be scaffolded into this repo.

### Production invariant (non-negotiable)

> Every agent-generated action must be typed, traced, policy-checked, evidence-linked, risk-scored, approval-aware, and rollback-aware before it can affect the outside world.

### Target file structure (PRL-3 and beyond)

```
schemas/
  policy_constraint.schema.json     # machine-readable governance rules
  capability_grant.schema.json      # least-privilege authority per agent/tool
  agent_role.schema.json            # normalizes role taxonomy
  agent_combination.schema.json     # multi-agent composition, max depth, fallbacks
  telemetry_event.schema.json       # required observability fields
  action_ledger_entry.schema.json   # auditable action records
  content_asset.schema.json         # publishing assets with hashes + review states
  improvement_proposal.schema.json  # prevents direct self-modification

src/
  policy_kernel.py      # deterministic policy evaluation: allow / deny / escalate / approval
  production_gate.py    # wraps policy eval, telemetry emission, action-ledger recording

examples/
  policy_constraints.json   # publication approval, finance denial, data-sharing escalation
  capability_grants.json    # draft, publishing preflight, market read-only grants

tests/
  run_validation.py          # aggregate validation (schemas, examples, behavior, telemetry, ledger)
  test_policy_kernel.py      # unit tests for core policy behavior

deploy/
  Dockerfile
  docker-compose.yml
  production_deployment_guide.md

.github/workflows/validate.yml    # CI: validation + pytest

security/
  security_verification_checklist.md
```

### Safety gates — hardcoded denials until compliance is implemented

| Action type | Required outcome |
|---|---|
| Autonomous crypto / finance trade | **Deny** |
| External publication | **Escalate** or require approval |
| Prompt-injection content detected | **Escalate** |
| Budget overage | Require approval or escalate |
| Domain-scope violation | **Deny** |
| Health / cannabis dosing | **Deny** |
| Destructive actions | **Deny** |

The capability grant check (least-privilege) must fire **before** the budget gate — an agent without the right grant is denied before spending limits are even evaluated.

### Implementation notes from hardening

- Normalize policy result values: internal `deny` → `denied` in action-ledger schema (use `normalize_policy_result()`).
- Preserve `escalate` as a distinct outcome — do not collapse it into `approval-required`.
- The first live production mode must be **draft-only with approval-required external actions**. Low-risk automation unlocks only after: zero critical violations, telemetry completeness > 99%, completion-under-policy > 95%, prompt-injection pass rate 100%, low owner override rate.

### Production services required (PRL-3+)

- **PostgreSQL** — policy versions, grants, action ledger, approval states, telemetry metadata
- **Object storage** — artifacts, hashes, screenshots, validation reports
- **Policy API** — validates proposed actions before any worker or connector executes them
- **Queue worker** — approved jobs with retries, rate limits, circuit breakers
- **Owner dashboard** — approvals, risks, ROI, kill switch
- **Connector wrappers** — gate Gmail, Drive, KDP, payment, browser, and publishing actions

### PRL ladder

| Level | Meaning | Status |
|---|---|---|
| PRL-0 | Concept only | Complete |
| PRL-1 | Source-grounded architecture and evidence matrix | Complete |
| PRL-2 | Working schemas, policy kernel, validation tests | Complete (externally; needs scaffolding here) |
| PRL-3 | Durable database and authenticated API | **Next** |
| PRL-4 | Owner dashboard and approval queue | Next |
| PRL-5 | Sandboxed Phoenix draft worker integrated | Next |
| PRL-6 | Production queue, audit job, monitoring | Later |
| PRL-7 | Low-risk automation with canary rollout | Later, after metrics prove safety |
| PRL-8 | Mature production agent OS | Future |

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

## System Architecture — Eight Planes

The target system is a **governed agent OS** structured as eight planes. Each plane has exactly one responsibility and one primary failure mode it controls.

| Plane | Responsibility | Primary failure mode controlled |
|---|---|---|
| **Owner & Portfolio** | Organize goals, domains, assets, next-best actions | Strategic fragmentation |
| **Governance** | Decide allow / escalate / block / log for every action | Ethical ambiguity and excessive agency |
| **Observability** | Capture causal traces of all events and actions (AOTP format) | Unreconstructable state history |
| **Agent Role** | Define bounded roles and valid agent combinations | Uncontrolled swarm complexity |
| **Production Pipeline** | Generate draft assets, reports, content, preflight packages | Low-quality or unverified output |
| **Execution** | Run jobs with queues, retries, rate limits, circuit breakers | Runaway automation |
| **Improvement** | Convert metrics into governed improvement proposals | Unsafe self-modification |
| **Interface** | Give owner visibility, approvals, and kill-switch control | Loss of human control |

### Component role remapping

| Existing material | Becomes |
|---|---|
| Phoenix/Kimi agent-chain | **Phoenix Draft Factory** — sandboxed draft-generation subsystem only |
| SOA Agent Combination Guide | **Agent Role and Combination Standard** |
| Compliant.AI / MEEF | **Governance and Entropy-Control Plane** |
| AOTP telemetry schema | **Telemetry and Action Ledger Plane** |
| Gemini roadmap | **Portfolio Navigation and Backlog Plane** |

### Governed control loop (Plan-Do-Check-Act)

```
1.  Owner intent → portfolio backlog
2.  Intent resolver → domain, risk class, allowed agent combination
3.  Governance plane → validate action against policy schema (allow / deny / escalate)
4.  If allowed → production pipeline generates draft artifact in isolated workspace
5.  Quality/compliance gates → evidence, originality, platform fit, preflight
6.  Execution plane → store draft, request approval, schedule job, or perform low-risk action
7.  Observability plane → AOTP telemetry + action-ledger entry for every event
8.  Improvement plane → analyze outcomes, emit proposals (never direct self-modification)
9.  Proposals → tests + red-team + regression + owner approval before promotion
10. Daily entropy audit → drift, budgets, failures, dependency health
```

### Domain autonomy ceilings

| Domain | Allowed now | Forbidden until governance matures |
|---|---|---|
| AI Agents & Engineering | Draft architectures, tests, docs, code-review checklists | Autonomous deployment without CI/security gates |
| Publishing & Writing | Draft, edit, format, hash, preflight, prepare metadata | Upload/publish without human approval |
| Passive Income & Automation | Research opportunities, draft funnels, generate assets | Spending, posting, purchasing, account changes without approval |
| Trading & Finance | Education, risk reports, simulations, portfolio summaries | Autonomous trading, transfers, tax decisions, regulated financial advice |
| Cannabis & Mycology | General educational content, literature summaries | Personalized medical/dosing decisions or jurisdiction-sensitive claims |
| Technical Development | Dev setup, dashboards, automation scripts, monitoring | Scripts with broad filesystem/credential access without sandboxing |
| Creative & Design | Visual briefs, brand concepts, content assets | Public publication or client delivery without review |
| Local/Practical Logistics | Research and planning | Purchases, permits, legal filings, contractor commitments without approval |

### Phoenix/Kimi redesign rules

| Existing component | Keep | Redesign requirement |
|---|---|---|
| Chain registry | Keep as opportunity catalog | Add risk labels, compliance tags, evidence requirements |
| Seven-agent swarm | Keep as role-template library | Register roles in SOA schema; restrict tools per role |
| CrewAI sequential pipeline | Keep for draft generation | Execute in sandbox; emit AOTP telemetry; store as content assets |
| Auto-executor retry logic | Keep pattern | Move to durable queue; policy checks before schedule and before execution |
| RSI engine | Keep metrics heuristics | Convert recommendations to improvement proposals requiring validation |
| Inference superposition | Rename/reframe | Treat as `MultiBranchDecisionExplorer`; add safety/evidence scoring |
| Frontend dashboard | Keep visual inspiration only | Rebuild around real APIs, approvals, telemetry, queues, audit logs |
| Mock research fallbacks | Keep only for tests | Must be labeled; prohibited from evidence gates in production |

### Governance object schemas (required fields)

| Object | Required fields |
|---|---|
| `PolicyConstraint` | `id`, `type`, `applies_to`, `trigger_condition`, `consequence`, `version`, `tests` |
| `CapabilityGrant` | `principal`, `tool`, `operation`, `data_scope`, `domain_scope`, `duration`, `budget`, `approval_rule` |
| `AgentCombination` | `canonical_name`, `abbreviation_combo`, `pipeline_order`, `oversight_checkpoints`, `fallback`, `test_harness` |
| `TelemetryEvent` | `event_id`, Lamport timestamp, wall-clock timestamp, `source`, `type`, `severity`, `payload_hash` |
| `ActionLedgerEntry` | `goal`, `actor`, `tool`, `policy_result`, `evidence_refs`, `approval_state`, `result`, `rollback_status` |
| `EntropyBudget` | `system`, `baseline`, `current_value`, `threshold`, `drift`, `escalation_action` |
| `ImprovementProposal` | `source_metric`, `diagnosis`, `change`, `expected_impact`, `risk_delta`, `tests`, `rollout_state` |

### Validation metrics and thresholds

| Metric | Threshold required before increased autonomy |
|---|---|
| Completion Under Policy | ≥ 95% for low-risk workflows; zero critical violations |
| Confirmation recall (high-impact actions sent to approval) | ≥ 98% for publication, finance, external comms, data sharing |
| Evidence validity rate | ≥ 95% for publishing/research outputs |
| Mock-data leakage rate | 0% |
| Telemetry completeness | ≥ 99% |
| Rollback success | ≥ 95% |
| Rule determinism | 100% for deterministic rules |
| Improvement safety | 100% for promoted changes |
| Owner override rate | Trending downward without lowering safety |

### Build order with acceptance criteria

| # | Module | Acceptance criterion |
|---|---|---|
| 1 | Git/ADR/CI/SBOM baseline | All code versioned; CI runs lint/tests; SBOM generated |
| 2 | Policy kernel | JSON Schema validates sample actions; rejects violations |
| 3 | AOTP/action ledger | Every action emits minimum telemetry and ledger entry |
| 4 | Role and combo registry | Each agent has id, abbreviation, allowed tools, output contract |
| 5 | Phoenix draft worker | Content chain runs in sandbox; produces versioned draft artifacts |
| 6 | Publishing preflight | Content hash, source list, originality check, metadata checklist, approval |
| 7 | Approval dashboard | Pending actions show evidence, risk, policy result, approve/reject |
| 8 | RSI/reflection bridge | Recommendations become proposals, not direct behavior changes |
| 9 | Durable executor | Jobs are policy-gated, persisted, cancellable, retried, circuit-broken |
| 10 | Daily entropy audit | Signed daily report lists budgets, anomalies, remediation |

**Integration order**: governance → telemetry → role taxonomy → Phoenix draft → publishing preflight → durable execution → recursive improvement.

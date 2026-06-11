# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

Install dependencies and start the backend:

```bash
pip install -r requirements.txt
python main.py
```

The API runs at `http://0.0.0.0:8000`. Open `dashboard.html` directly in a browser — it is a static file, not served by FastAPI, and hardcodes `http://127.0.0.1:8000` as its backend URL.

There are no tests, no linting configuration, and no build step.

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

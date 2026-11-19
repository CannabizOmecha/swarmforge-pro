# SwarmForge

A mixture-of-experts agent swarm that turns a goal into one concrete, pressure-tested next step.

```
goal ─▶ 5 experts propose in parallel ─▶ red team critiques each ─▶ judge picks + states dissent
                                                                      │
                                   reversible? ── yes ─▶ completed (recommendation)
                                               └─ no ──▶ awaiting_approval ─▶ human approves/rejects
```

## Design principles

- **The swarm recommends; it never acts.** No tool can spend money, publish, or contact anyone.
- **Irreversible = human decision.** Any plan with an irreversible step waits for explicit approval.
- **Typed contracts.** Every agent output is JSON-schema constrained and re-validated with pydantic; invalid output is rejected, not guessed at.
- **Failure containment.** One expert failing doesn't sink the run; if nothing survives critique, the run says so.
- **Tamper-evident audit.** Every run and human decision is appended to a SHA-256 hash-chained log (`/health` reports integrity).
- **No theatre.** No hardcoded "SUCCESS" or revenue numbers. Demo mode is explicit and labelled.

## Run

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                               # offline, no API key needed
SWARMFORGE_DEMO=1 python main.py        # offline demo at http://127.0.0.1:8000
ANTHROPIC_API_KEY=... python main.py    # live, uses Claude
```

Env: `SWARMFORGE_MODEL` (default `claude-opus-5-5`), `SWARMFORGE_AUDIT` (default `audit/log.jsonl`).
Live mode enables Claude's server-side refusal fallback (`fallbacks: "default"`); remove it in `swarmforge/llm.py` if unwanted.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Dashboard |
| GET | `/health` | Mode + audit-chain integrity |
| POST | `/runs` `{"goal": "..."}` | Run the swarm |
| GET | `/runs/{id}` | Fetch a run |
| POST | `/runs/{id}/decision` `{"approve": true}` | Human sign-off for irreversible plans |

## Known limits / next steps

- Runs are kept in memory (lost on restart); persist them (SQLite) next.
- No auth on the API; bind to localhost only until you add it.
- `/runs` is synchronous (a live run makes ~11 model calls); move to background jobs for production.
- Add an eval set of real goals to measure whether the judge's picks actually beat a single agent.

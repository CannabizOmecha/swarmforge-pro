# SwarmForge Pro 3.0

A small async agent swarm with full visibility into its own state (**omniscience**) and a
control plane that can act on any agent (**omnipotence**), where irreversible actions need a human to approve them.

```bash
pip install -r requirements.txt
python main.py            # http://localhost:8000/dashboard  ·  API docs at /docs
```

## Omniscience: see everything
| Route | What it shows |
|---|---|
| `GET /health` | liveness + live agent count |
| `GET /omniscience/state` | agents, queue depths, task stats, pending approvals, revenue, process metrics |
| `GET /omniscience/tasks?status=&role=` / `GET /omniscience/tasks/{id}` | task history with results and errors |
| `GET /omniscience/events?since=&kind=` | ordered event log (ring buffer, 2000 events) |
| `GET /omniscience/stream` | live Server-Sent Events of every state change |

## Omnipotence: act on anything
Direct (reversible): `POST /omnipotence/tasks`, `/broadcast`, `/tasks/{id}/cancel`,
`/agents/{role}` (spawn), `/roles/{role}/scale`, `/agents/{id}/pause`, `/agents/{id}/resume`.

Irreversible actions (`stop_agent`, `purge_queue`, `record_revenue`) are **proposed** with
`POST /omnipotence/proposals` and only run after `POST /omnipotence/proposals/{id}/decide {"approve": true}`.

Set `SWARMFORGE_ADMIN_TOKEN` to require an `X-Admin-Token` header on every control-plane route.
Do this anywhere the server is reachable by other people.

## Plugging in real work
Each role uses a built-in placeholder handler. Swap one in with a real handler:
```python
async def write_copy(task):           # e.g. call an LLM, run a build, query a DB
    return {"copy": "..."}
main.swarm.register_handler("marketer", write_copy)
```

## Revenue
`/revenue` reports only amounts that were actually recorded (and approved). The run-rate projection
stays `null` until there are at least two entries. Earlier versions returned a hardcoded `$3790/month`.

## Tests
```bash
pip install -r requirements-dev.txt && python -m pytest -q
```

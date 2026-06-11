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

### Domain model (as represented in `/deploy` response)

The four agents map to business roles:

| Agent key    | Type          | Role       |
|------------- |---------------|------------|
| `developer`  | NeuroSymbolic | Engineering |
| `marketer`   | Causal        | Marketing  |
| `analyst`    | Quantum       | Analysis   |
| `compliance` | Formal        | Compliance |

All agent state and revenue figures (`$3790/month`, SVY `4.2`) are currently hardcoded — there is no database or external service.

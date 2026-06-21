# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

SwarmForge Pro is a minimal two-piece demo: a FastAPI backend (`main.py`) and a static HTML dashboard (`dashboard.html`) that calls it. There is no build system, test suite, linter config, or CI — the entire codebase is three files.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the backend (serves on http://0.0.0.0:8000)
python main.py
# — or —
uvicorn main:app --reload --port 8000

# View the dashboard
# Open dashboard.html directly in a browser. It fetches from
# http://127.0.0.1:8000, so the backend must already be running on that exact host:port.
```

There are no tests or linters configured in this repo.

## Architecture

- **`main.py`** — FastAPI app with three routes: `GET /`, `POST /deploy`, `GET /revenue`. All responses are hardcoded dictionaries (no real agent logic, no database, no auth) — `/deploy` and `/revenue` simulate output rather than compute it.
- **`dashboard.html`** — a single static file with no build step. Loads Tailwind via CDN and uses vanilla JS `fetch` calls (no framework) to hit the backend at the hardcoded URL `http://127.0.0.1:8000`. The backend has no CORS middleware configured, so requests from a different origin/port than expected will fail silently in the browser (the dashboard's `catch` block just renders "ERROR: Backend not running").
- The two halves are fully decoupled processes — backend and dashboard must be run/opened independently; nothing wires them together besides that hardcoded URL.

## Notes on repo state

- `requirements.txt` pins no versions (`fastapi`, `uvicorn[standard]`).
- A compiled `__pycache__/main.cpython-313.pyc` is currently committed to git; there is no `.gitignore`.

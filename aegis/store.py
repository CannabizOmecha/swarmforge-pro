from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import EvidenceRecord, Finding, RunRecord


class Store:
    def __init__(self, path: str = "data/aegis.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init(self):
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    def save_run(self, run: RunRecord):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO runs VALUES (?, ?)", (run.run_id, run.model_dump_json()))

    def save_finding(self, finding: Finding):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO findings VALUES (?, ?)", (finding.finding_id, finding.model_dump_json()))

    def save_evidence(self, evidence: EvidenceRecord):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO evidence VALUES (?, ?)", (evidence.evidence_id, evidence.model_dump_json()))

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_findings(self) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT payload FROM findings ORDER BY rowid DESC").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def counts(self) -> dict[str, int]:
        with self._connect() as db:
            return {
                "runs": db.execute("SELECT count(*) FROM runs").fetchone()[0],
                "findings": db.execute("SELECT count(*) FROM findings").fetchone()[0],
                "evidence": db.execute("SELECT count(*) FROM evidence").fetchone()[0],
            }

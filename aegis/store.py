from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import EvidenceRecord, Finding, RunRecord


class Store:
    """Small transactional store for the single-node MVP."""

    def __init__(self, path: str = "data/aegis.sqlite3"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init(self):
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS findings (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
            """)

    def save_bundle(self, run: RunRecord, findings: list[Finding], evidence: list[EvidenceRecord]):
        """Persist a run and its outputs atomically; never expose a partially saved run."""
        with self._connect() as db, db:
            db.execute("INSERT INTO runs VALUES (?, ?)", (run.run_id, run.model_dump_json()))
            db.executemany(
                "INSERT INTO findings VALUES (?, ?)",
                [(item.finding_id, item.model_dump_json()) for item in findings],
            )
            db.executemany(
                "INSERT INTO evidence VALUES (?, ?)",
                [(item.evidence_id, item.model_dump_json()) for item in evidence],
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def get_evidence(self, evidence_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT payload FROM evidence WHERE id=?", (evidence_id,)).fetchone()
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

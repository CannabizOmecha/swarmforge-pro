from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .models import EvidenceRecord, Finding, RunRecord


class Store:
    """Transactional SQLite store for the single-node synthetic MVP."""

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
                CREATE TABLE IF NOT EXISTS idempotency (
                    key TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    response_payload TEXT NOT NULL
                );
            """)

    def save_bundle(
        self,
        run: RunRecord,
        findings: list[Finding],
        evidence: list[EvidenceRecord],
        *,
        idempotency_key: str | None = None,
        request_fingerprint: str | None = None,
        response_payload: dict[str, Any] | None = None,
    ):
        """Persist run outputs and optional idempotency result in one transaction."""
        if idempotency_key is not None and (
            request_fingerprint is None or response_payload is None
        ):
            raise ValueError("Idempotency metadata must be complete.")
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
            if idempotency_key is not None:
                db.execute(
                    "INSERT INTO idempotency VALUES (?, ?, ?)",
                    (
                        idempotency_key,
                        request_fingerprint,
                        json.dumps(response_payload, sort_keys=True, separators=(",", ":")),
                    ),
                )

    def get_idempotency_result(self, key: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT fingerprint, response_payload FROM idempotency WHERE key=?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return {
            "fingerprint": row["fingerprint"],
            "response": json.loads(row["response_payload"]),
        }

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

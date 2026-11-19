"""Append-only, hash-chained audit log: every run and every human decision is tamper-evident."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path


class AuditLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _last_hash(self) -> str:
        if not self.path.exists():
            return "0" * 64
        last = None
        with self.path.open() as f:
            for line in f:
                if line.strip():
                    last = line
        return json.loads(last)["hash"] if last else "0" * 64

    def append(self, event: str, data: dict) -> str:
        with self._lock:
            prev = self._last_hash()
            body = {"ts": time.time(), "event": event, "data": data, "prev": prev}
            h = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
            body["hash"] = h
            with self.path.open("a") as f:
                f.write(json.dumps(body, sort_keys=True) + "\n")
            return h

    def verify(self) -> bool:
        prev = "0" * 64
        if not self.path.exists():
            return True
        with self.path.open() as f:
            for line in f:
                if not line.strip():
                    continue
                rec = json.loads(line)
                h = rec.pop("hash")
                if rec["prev"] != prev:
                    return False
                if hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest() != h:
                    return False
                prev = h
        return True

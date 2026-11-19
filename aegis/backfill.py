"""Safe, dry-run-first reconciliation of historical finding groups."""
from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import Finding
from .store import Store

_GROUP_COLUMNS = (
    "fingerprint",
    "property_id",
    "state",
    "security_impact",
    "expected",
    "actual",
    "first_seen_at",
    "last_seen_at",
    "occurrence_count",
    "first_run_id",
    "last_run_id",
    "last_finding_id",
)


def _utc_created_at(finding: Finding) -> datetime:
    value = finding.created_at
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _expected_groups(rows: list[Any]) -> list[dict[str, Any]]:
    findings: list[tuple[datetime, Finding]] = []
    for row in rows:
        finding = Finding.model_validate_json(row["payload"])
        if finding.finding_id != row["id"]:
            raise ValueError("Stored finding identifier does not match its payload.")
        findings.append((_utc_created_at(finding), finding))

    findings.sort(key=lambda item: (item[0], item[1].finding_id))
    groups: dict[str, dict[str, Any]] = {}
    from .dedup import finding_fingerprint

    for created_at, finding in findings:
        fingerprint = finding_fingerprint(finding)
        timestamp = created_at.isoformat()
        group = groups.get(fingerprint)
        if group is None:
            groups[fingerprint] = {
                "fingerprint": fingerprint,
                "property_id": finding.property_id,
                "state": finding.state.value,
                "security_impact": finding.security_impact,
                "expected": finding.expected,
                "actual": finding.actual,
                "first_seen_at": timestamp,
                "last_seen_at": timestamp,
                "occurrence_count": 1,
                "first_run_id": finding.run_id,
                "last_run_id": finding.run_id,
                "last_finding_id": finding.finding_id,
            }
        else:
            group["last_seen_at"] = timestamp
            group["occurrence_count"] += 1
            group["last_run_id"] = finding.run_id
            group["last_finding_id"] = finding.finding_id
    return [groups[key] for key in sorted(groups)]


def rebuild_finding_groups(store: Store, *, apply: bool = False) -> dict[str, Any]:
    """Preview or atomically rebuild the derived index from validated findings.

    Apply mode locks writers before reading source rows. No group rows are changed
    until every source finding has passed strict validation.
    """
    with store._connect() as db:
        if apply:
            db.execute("BEGIN IMMEDIATE")
        source_rows = db.execute("SELECT id, payload FROM findings").fetchall()
        expected = _expected_groups(source_rows)
        existing_rows = db.execute(
            "SELECT * FROM finding_groups ORDER BY fingerprint"
        ).fetchall()
        existing = [dict(row) for row in existing_rows]
        expected_by_columns = [
            {column: group[column] for column in _GROUP_COLUMNS} for group in expected
        ]
        changed = existing != expected_by_columns
        if apply and changed:
            db.execute("DELETE FROM finding_groups")
            db.executemany(
                """
                INSERT INTO finding_groups (
                    fingerprint, property_id, state, security_impact,
                    expected, actual, first_seen_at, last_seen_at,
                    occurrence_count, first_run_id, last_run_id, last_finding_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    tuple(group[column] for column in _GROUP_COLUMNS)
                    for group in expected_by_columns
                ],
            )
            store._append_audit_event(
                db,
                "finding_groups.rebuilt",
                "finding-groups",
                {
                    "source_finding_count": len(source_rows),
                    "group_count": len(expected_by_columns),
                    "previous_group_count": len(existing),
                },
            )

    return {
        "mode": "apply" if apply else "dry_run",
        "changed": changed,
        "applied": bool(apply and changed),
        "source_finding_count": len(source_rows),
        "expected_group_count": len(expected_by_columns),
        "previous_group_count": len(existing),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview or rebuild the local AEGIS finding-group index."
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data/aegis.sqlite3"),
        help="Existing local SQLite database (default: data/aegis.sqlite3).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply the atomic rebuild; without this flag the command is read-only.",
    )
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error(f"database does not exist: {args.database}")
    result = rebuild_finding_groups(Store(str(args.database)), apply=args.apply)
    print(json.dumps(result, sort_keys=True))
    if result["changed"] and not args.apply:
        print("Dry run only: review the counts, then rerun with --apply to rebuild.")


if __name__ == "__main__":
    main()

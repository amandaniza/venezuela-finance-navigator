"""
Import navigator_funding_seed.json into the funding_sources table.

The seed holds 25 researched, UNVERIFIED funding leads. This importer:
  * maps every JSON key to a funding_sources column (no forcing into funds_tb),
  * preserves verification_status verbatim (nothing becomes a Green/Red verdict),
  * records currency + original amounts for the non-USD entries (DEC=GBP,
    IFRC=CHF, EU=EUR) so the UI can label converted figures with "≈",
  * stamps last_checked (default 2026-07-04) on every row.

Idempotent: upserts on source_key.

Usage (from repo root):
    python scripts/import_funding_seed.py
    python scripts/import_funding_seed.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from database import get_connection, init_db

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("import_funding_seed")

_COLUMNS = [
    "source_key", "name_en", "name_es", "org", "org_type", "category",
    "flow_direction", "amount_target_usd", "amount_committed_usd",
    "amount_notes", "currency", "amount_target_original",
    "amount_committed_original", "status", "expires", "accepts_from",
    "funds_go_to", "compliance_notes", "suggested_license",
    "verification_status", "url", "phase", "notes_es", "last_checked",
    "accepts_applications", "applicant_tier", "how_to_apply",
    "how_to_apply_es",
]


def _accepts_applications(entry: dict) -> int | None:
    """Human-set tag for the NGO funding-seeking view.

    Only honored when the key is present in the seed entry (a person tagged
    it); absent means "not yet confirmed" (NULL). Never derived from
    flow_direction — see the funding_sources schema note.
    """
    if "accepts_applications" not in entry:
        return None
    return 1 if entry["accepts_applications"] else 0


def _row_from_entry(entry: dict) -> dict:
    key = entry["id"]
    override = config.FUNDING_CURRENCY_OVERRIDES.get(key, {})
    return {
        "source_key": key,
        "name_en": entry.get("name_en") or entry.get("name") or key,
        "name_es": entry.get("name_es") or "",
        "org": entry.get("org") or "",
        "org_type": entry.get("org_type") or "",
        "category": entry.get("category") or "",
        "flow_direction": entry.get("flow_direction") or "",
        "amount_target_usd": entry.get("amount_target_usd"),
        "amount_committed_usd": entry.get("amount_committed_usd"),
        "amount_notes": entry.get("amount_notes") or "",
        "currency": override.get("currency", "USD"),
        "amount_target_original": override.get("amount_target_original"),
        "amount_committed_original": override.get("amount_committed_original"),
        "status": entry.get("status") or "",
        "expires": entry.get("expires"),
        "accepts_from": json.dumps(entry.get("accepts_from") or [], ensure_ascii=False),
        "funds_go_to": entry.get("funds_go_to") or "",
        "compliance_notes": entry.get("compliance_notes") or "",
        # Deliberately free text, NOT a join to licenses_tb.
        "suggested_license": entry.get("suggested_license_pathway") or "",
        # Preserve verbatim — never coerce to a verdict.
        "verification_status": entry.get("verification_status") or "unverified",
        "url": entry.get("url") or "",
        "phase": json.dumps(entry.get("phase") or [], ensure_ascii=False),
        "notes_es": entry.get("notes_es") or "",
        "last_checked": config.FUNDING_LAST_CHECKED,
        "accepts_applications": _accepts_applications(entry),
        "applicant_tier": entry.get("applicant_tier") or None,
        "how_to_apply": entry.get("how_to_apply") or "",
        "how_to_apply_es": entry.get("how_to_apply_es") or "",
    }


def _upsert(conn, row: dict) -> str:
    existing = conn.execute(
        "SELECT id FROM funding_sources WHERE source_key = ?",
        (row["source_key"],),
    ).fetchone()
    if existing:
        assignments = ", ".join(f"{c} = ?" for c in _COLUMNS if c != "source_key")
        params = [row[c] for c in _COLUMNS if c != "source_key"]
        params.append(row["source_key"])
        conn.execute(
            f"UPDATE funding_sources SET {assignments} WHERE source_key = ?", params
        )
        return "updated"
    placeholders = ", ".join("?" for _ in _COLUMNS)
    conn.execute(
        f"INSERT INTO funding_sources ({', '.join(_COLUMNS)}) VALUES ({placeholders})",
        [row[c] for c in _COLUMNS],
    )
    return "inserted"


def import_seed(*, dry_run: bool = False) -> dict:
    path = config.FUNDING_SEED_PATH
    if not path.exists():
        raise FileNotFoundError(f"Seed file not found: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("funding_sources") or []
    log.info("Loaded %d funding source(s) from %s", len(entries), path.name)

    if dry_run:
        for e in entries:
            row = _row_from_entry(e)
            log.info(
                "DRY %-28s cur=%-3s committed_usd=%s status=%s",
                row["source_key"], row["currency"],
                row["amount_committed_usd"], row["verification_status"],
            )
        return {"total": len(entries), "inserted": 0, "updated": 0}

    init_db()
    counts = {"inserted": 0, "updated": 0}
    with get_connection() as conn:
        for e in entries:
            counts[_upsert(conn, _row_from_entry(e))] += 1
        conn.commit()
    log.info(
        "Import complete: %d inserted, %d updated",
        counts["inserted"], counts["updated"],
    )
    return {"total": len(entries), **counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Import funding directory seed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    summary = import_seed(dry_run=args.dry_run)
    log.info("Summary: %s", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
SQLite database layer for the Venezuela Reconstruction Finance Navigator.

Schema: licenses_tb, funds_tb, pathways_tb.
Human_Verified defaults to False (0) on all tables.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "data" / "navigator.db"

SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS licenses_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    License_ID TEXT NOT NULL UNIQUE,
    Status TEXT,
    Expiration_Date TEXT,
    Authorized_Activities TEXT,
    Excluded_Entities TEXT,
    Source_URL TEXT,
    Content_Hash TEXT,
    Raw_Snippet TEXT,
    Human_Verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS funds_tb (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    Fund_Name TEXT NOT NULL,
    Capital_Type TEXT,
    Target_Sectors TEXT,
    Donor TEXT,
    Recipient_Org TEXT,
    Amount_USD REAL,
    Status TEXT,
    Source_Name TEXT,
    Source_URL TEXT,
    Content_Hash TEXT,
    Raw_Snippet TEXT,
    Human_Verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS pathways_tb (
    Map_ID INTEGER PRIMARY KEY AUTOINCREMENT,
    Linked_Fund INTEGER NOT NULL,
    Governing_License INTEGER NOT NULL,
    Compliance_Verdict TEXT,
    Human_Verified INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (Linked_Fund) REFERENCES funds_tb(id),
    FOREIGN KEY (Governing_License) REFERENCES licenses_tb(id)
);

-- Researched, human-curated funding directory (navigator_funding_seed.json).
-- These are UNVERIFIED leads: verification_status is preserved verbatim and
-- suggested_license is free text, deliberately NOT a join to licenses_tb.
-- Nothing here is a Green/Red verdict; that lives only in pathways_tb.
CREATE TABLE IF NOT EXISTS funding_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_key TEXT NOT NULL UNIQUE,
    name_en TEXT NOT NULL,
    name_es TEXT,
    org TEXT,
    org_type TEXT,
    category TEXT,
    flow_direction TEXT,
    amount_target_usd REAL,
    amount_committed_usd REAL,
    amount_notes TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    amount_target_original REAL,
    amount_committed_original REAL,
    status TEXT,
    expires TEXT,
    accepts_from TEXT,          -- JSON array
    funds_go_to TEXT,
    compliance_notes TEXT,
    suggested_license TEXT,     -- free-text pathway hint, NOT an FK
    verification_status TEXT NOT NULL,
    url TEXT,
    phase TEXT,                 -- JSON array
    notes_es TEXT,
    last_checked TEXT,
    -- NGO funding-seeking path: 1 = confirmed accepting applications/proposals
    -- from implementing organizations, 0 = confirmed not, NULL = not yet
    -- confirmed. Set ONLY from the seed (a human tagging decision) — never
    -- inferred from flow_direction or other fields.
    accepts_applications INTEGER
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# Columns added after the initial release, applied to already-existing DBs.
# table -> {name -> column definition (type + constraints, no name)}.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "funds_tb": {
        "Donor": "TEXT",
        "Recipient_Org": "TEXT",
        "Amount_USD": "REAL",
        "Status": "TEXT",
        "Source_Name": "TEXT",
    },
    "funding_sources": {
        "accepts_applications": "INTEGER",
        # Applicant-facing view (fd=seek): tier is "open" (structured
        # application an org can start today), "partnership" (funds local
        # orgs via relationship/invitation), or "enabler" (not a funder;
        # unlocks money from elsewhere). NULL = not applicant-facing.
        "applicant_tier": "TEXT",
        "how_to_apply": "TEXT",
        "how_to_apply_es": "TEXT",
        # Spanish translations of the two free-text detail fields, so the
        # source detail page is single-language (see item 2, 2026-07 edits).
        "funds_go_to_es": "TEXT",
        "compliance_notes_es": "TEXT",
    },
}


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after a DB was first created.

    SQLite has no ``ADD COLUMN IF NOT EXISTS``; we diff against the live
    schema via PRAGMA table_info and add whatever is missing. Idempotent.
    """
    for table, columns in _ADDED_COLUMNS.items():
        existing = {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, decl in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


# DB paths already initialized in this process. init_db is called by every
# fetch and every page render; running the DDL + migration on each call adds
# measurable latency to every rerun, so it executes once per path per process.
_INITIALIZED: set[str] = set()


def init_db(db_path: Path | None = None) -> Path:
    """Create tables if they do not exist, then apply migrations. Returns path.

    Idempotent and cached: the schema script runs once per process per path.
    """
    path = db_path or DB_PATH
    key = str(path)
    if key in _INITIALIZED and path.exists():
        return path
    with get_connection(path) as conn:
        conn.executescript(SCHEMA_SQL)
        _migrate(conn)
        conn.commit()
    _INITIALIZED.add(key)
    return path


def _parse_json_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(v) for v in parsed]
    except (json.JSONDecodeError, TypeError):
        pass
    return [str(value)]


def _row_to_pathway(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "map_id": row["Map_ID"],
        "fund_name": row["Fund_Name"] or "",
        "capital_type": row["Capital_Type"] or "",
        "target_sectors": _parse_json_list(row["Target_Sectors"]),
        "license_id": row["License_ID"] or "",
        "license_status": row["Status"] or "",
        "expiration_date": row["Expiration_Date"],
        "compliance_verdict": row["Compliance_Verdict"] or "",
        "authorized_activities": _parse_json_list(row["Authorized_Activities"]),
        "excluded_entities": row["Excluded_Entities"] or "",
        "human_verified": bool(row["Human_Verified"]),
        "linked_fund_id": row["Linked_Fund"],
        "governing_license_id": row["Governing_License"],
    }


_PATHWAY_JOIN_SQL = """
SELECT
    p.Map_ID,
    p.Linked_Fund,
    p.Governing_License,
    p.Compliance_Verdict,
    p.Human_Verified,
    f.Fund_Name,
    f.Capital_Type,
    f.Target_Sectors,
    l.License_ID,
    l.Status,
    l.Expiration_Date,
    l.Authorized_Activities,
    l.Excluded_Entities
FROM pathways_tb p
LEFT JOIN funds_tb f ON f.id = p.Linked_Fund
LEFT JOIN licenses_tb l ON l.id = p.Governing_License
"""


def fetch_pathways_for_admin(db_path: Path | None = None) -> list[dict[str, Any]]:
    """All pathways with fund/license labels for the Admin data editor."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            _PATHWAY_JOIN_SQL + " ORDER BY p.Map_ID ASC"
        ).fetchall()
    return [_row_to_pathway(r) for r in rows]


def fetch_verified_pathways(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Pathways with Human_Verified = 1 for the public Navigator."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            _PATHWAY_JOIN_SQL + " WHERE p.Human_Verified = 1 ORDER BY p.Map_ID ASC"
        ).fetchall()
    return [_row_to_pathway(r) for r in rows]


def _row_to_fund(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "fund_name": row["Fund_Name"] or "",
        "capital_type": row["Capital_Type"] or "",
        "target_sectors": _parse_json_list(row["Target_Sectors"]),
        "donor": row["Donor"] or "",
        "recipient_org": row["Recipient_Org"] or "",
        "amount_usd": row["Amount_USD"],
        "status": row["Status"] or "",
        "source_name": row["Source_Name"] or "",
        "source_url": row["Source_URL"] or "",
        "human_verified": bool(row["Human_Verified"]),
    }


_FUNDING_COLUMNS = (
    "source_key, name_en, name_es, org, org_type, category, flow_direction, "
    "amount_target_usd, amount_committed_usd, amount_notes, currency, "
    "amount_target_original, amount_committed_original, status, expires, "
    "accepts_from, funds_go_to, compliance_notes, suggested_license, "
    "verification_status, url, phase, notes_es, last_checked, "
    "accepts_applications, applicant_tier, how_to_apply, how_to_apply_es, "
    "funds_go_to_es, compliance_notes_es"
)


def _row_to_funding_source(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "source_key": row["source_key"],
        "name_en": row["name_en"] or "",
        "name_es": row["name_es"] or "",
        "org": row["org"] or "",
        "org_type": row["org_type"] or "",
        "category": row["category"] or "",
        "flow_direction": row["flow_direction"] or "",
        "amount_target_usd": row["amount_target_usd"],
        "amount_committed_usd": row["amount_committed_usd"],
        "amount_notes": row["amount_notes"] or "",
        "currency": row["currency"] or "USD",
        "amount_target_original": row["amount_target_original"],
        "amount_committed_original": row["amount_committed_original"],
        "status": row["status"] or "",
        "expires": row["expires"],
        "accepts_from": _parse_json_list(row["accepts_from"]),
        "funds_go_to": row["funds_go_to"] or "",
        "funds_go_to_es": row["funds_go_to_es"] or "",
        "compliance_notes": row["compliance_notes"] or "",
        "compliance_notes_es": row["compliance_notes_es"] or "",
        "suggested_license": row["suggested_license"] or "",
        "verification_status": row["verification_status"] or "unverified",
        "url": row["url"] or "",
        "phase": _parse_json_list(row["phase"]),
        "notes_es": row["notes_es"] or "",
        # None = not yet confirmed by a human; never inferred (see schema).
        "accepts_applications": row["accepts_applications"],
        "applicant_tier": row["applicant_tier"] or "",
        "how_to_apply": row["how_to_apply"] or "",
        "how_to_apply_es": row["how_to_apply_es"] or "",
        "last_checked": row["last_checked"] or "",
    }


def fetch_funding_sources(db_path: Path | None = None) -> list[dict[str, Any]]:
    """All directory entries. Filtering (flow/phase/org_type) happens in the UI."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT {_FUNDING_COLUMNS} FROM funding_sources "
            "ORDER BY "
            "  CASE WHEN amount_committed_usd IS NULL THEN 1 ELSE 0 END, "
            "  amount_committed_usd DESC, name_en ASC"
        ).fetchall()
    return [_row_to_funding_source(r) for r in rows]


def fetch_funding_source(
    source_key: str, db_path: Path | None = None
) -> dict[str, Any] | None:
    """One directory entry by its stable source_key (for the detail view)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            f"SELECT {_FUNDING_COLUMNS} FROM funding_sources WHERE source_key = ?",
            (source_key,),
        ).fetchone()
    return _row_to_funding_source(row) if row else None


def fetch_pathway(map_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    """One verified pathway by Map_ID (for the pathway detail view)."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        row = conn.execute(
            _PATHWAY_JOIN_SQL + " WHERE p.Map_ID = ?", (int(map_id),)
        ).fetchone()
    return _row_to_pathway(row) if row else None


def fetch_licenses(db_path: Path | None = None) -> list[dict[str, Any]]:
    """All licenses for the Navigator's license-snapshot cards, active first."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT License_ID, Status, Expiration_Date, Authorized_Activities
            FROM licenses_tb
            ORDER BY
                CASE Status
                    WHEN 'Active' THEN 0
                    WHEN 'Expiring Soon' THEN 1
                    WHEN 'Expired' THEN 2
                    WHEN 'Revoked' THEN 3
                    ELSE 4
                END,
                License_ID ASC
            """
        ).fetchall()
    return [
        {
            "license_id": r["License_ID"] or "",
            "status": r["Status"] or "",
            "expiration_date": r["Expiration_Date"],
            "activities": _parse_json_list(r["Authorized_Activities"]),
        }
        for r in rows
    ]


def fetch_public_funds(db_path: Path | None = None) -> list[dict[str, Any]]:
    """Human-verified funds/flows for the public Navigator capital-stack view.

    Returns every verified row in funds_tb — both open funding pools
    (no Recipient_Org) and allocated flows (Donor → Recipient_Org).
    """
    init_db(db_path)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, Fund_Name, Capital_Type, Target_Sectors, Donor,
                   Recipient_Org, Amount_USD, Status, Source_Name, Source_URL,
                   Human_Verified
            FROM funds_tb
            WHERE Human_Verified = 1
            ORDER BY
                CASE WHEN Amount_USD IS NULL THEN 1 ELSE 0 END,
                Amount_USD DESC,
                Fund_Name ASC
            """
        ).fetchall()
    return [_row_to_fund(r) for r in rows]


def update_pathway(
    map_id: int,
    compliance_verdict: str,
    human_verified: bool,
    db_path: Path | None = None,
) -> None:
    """Update Compliance_Verdict and Human_Verified for one pathway."""
    init_db(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            UPDATE pathways_tb
            SET Compliance_Verdict = ?, Human_Verified = ?
            WHERE Map_ID = ?
            """,
            (compliance_verdict, 1 if human_verified else 0, int(map_id)),
        )
        conn.commit()


def update_pathways_batch(
    rows: list[dict[str, Any]],
    db_path: Path | None = None,
) -> int:
    """
    Persist Admin editor rows.

    Each row must include map_id, compliance_verdict, human_verified.
    Returns the number of rows updated.
    """
    init_db(db_path)
    count = 0
    with get_connection(db_path) as conn:
        for row in rows:
            conn.execute(
                """
                UPDATE pathways_tb
                SET Compliance_Verdict = ?, Human_Verified = ?
                WHERE Map_ID = ?
                """,
                (
                    row.get("compliance_verdict") or row.get("Compliance_Verdict") or "",
                    1
                    if row.get("human_verified", row.get("Human_Verified", False))
                    else 0,
                    int(row["map_id"] if "map_id" in row else row["Map_ID"]),
                ),
            )
            count += 1
        conn.commit()
    return count

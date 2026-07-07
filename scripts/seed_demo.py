"""
Seed local SQLite (data/navigator.db) with demo licenses, funds, and pathways.

Safe to re-run: upserts by License_ID / Fund_Name / fund+license pair.

Usage (from repo root):
    python scripts/seed_demo.py
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import get_connection, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("seed_demo")

LICENSES = [
    {
        "License_ID": "GL 60",
        "Status": "Active",
        "Expiration_Date": "2026-10-23",
        "Authorized_Activities": [
            "earthquake relief efforts in Venezuela",
            "processing or transfer of funds on behalf of third-country "
            "persons to or from Venezuela in support of earthquake relief",
        ],
        "Source_URL": "https://ofac.treasury.gov/recent-actions/20260625_33",
        "Human_Verified": True,
    },
    {
        "License_ID": "GL 56",
        "Status": "Active",
        "Expiration_Date": "2027-02-01",
        "Authorized_Activities": ["Contingent contracts"],
        "Source_URL": None,
        "Human_Verified": False,
    },
    {
        # Backs the "send money to family" simple path, which deep-links to
        # this card. Covers only four named banks (BCV, Banco de Venezuela,
        # Banco Digital de los Trabajadores, Banco del Tesoro) + 50%-owned
        # entities; no stated expiry (both confirmed 2026-07-07). Activity
        # bullets still pending final wording — keep Human_Verified False
        # until they're confirmed.
        "License_ID": "GL 57",
        "Status": "Active",
        "Expiration_Date": None,
        "Authorized_Activities": [
            "financial services involving certain Venezuelan banks",
            "personal, non-commercial remittances to Venezuela",
        ],
        "Source_URL": "https://ofac.treasury.gov/recent-actions/20260414_33",
        "Human_Verified": False,
    },
]

FUNDS = [
    {
        "Fund_Name": "CAF Earthquake Reconstruction Seed Fund",
        "Capital_Type": "Grant",
        "Target_Sectors": ["Infrastructure", "WASH"],
        "Human_Verified": True,
    },
    {
        "Fund_Name": "IDB Resilient Housing Initiative",
        "Capital_Type": "Concessional Loan",
        "Target_Sectors": ["Housing"],
        "Human_Verified": False,
    },
]

# (fund_name, license_id, verdict, human_verified)
PATHWAYS = [
    (
        "CAF Earthquake Reconstruction Seed Fund",
        "GL 60",
        "Green",
        True,
    ),
    (
        "IDB Resilient Housing Initiative",
        "GL 56",
        "Yellow",
        True,
    ),
    (
        "IDB Resilient Housing Initiative",
        "GL 60",
        "Red",
        False,
    ),
]


def _json_list(values: list[str]) -> str:
    return json.dumps(values, ensure_ascii=False)


def upsert_license(conn, lic: dict) -> int:
    row = conn.execute(
        "SELECT id FROM licenses_tb WHERE License_ID = ?",
        (lic["License_ID"],),
    ).fetchone()
    activities = _json_list(lic["Authorized_Activities"])
    verified = 1 if lic["Human_Verified"] else 0

    if row:
        conn.execute(
            """
            UPDATE licenses_tb
            SET Status = ?,
                Expiration_Date = ?,
                Authorized_Activities = ?,
                Source_URL = COALESCE(?, Source_URL),
                Human_Verified = ?
            WHERE id = ?
            """,
            (
                lic["Status"],
                lic["Expiration_Date"],
                activities,
                lic.get("Source_URL"),
                verified,
                row["id"],
            ),
        )
        log.info("Updated license %s (id=%s)", lic["License_ID"], row["id"])
        return int(row["id"])

    cur = conn.execute(
        """
        INSERT INTO licenses_tb (
            License_ID, Status, Expiration_Date,
            Authorized_Activities, Source_URL, Human_Verified
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            lic["License_ID"],
            lic["Status"],
            lic["Expiration_Date"],
            activities,
            lic.get("Source_URL"),
            verified,
        ),
    )
    license_pk = int(cur.lastrowid)
    log.info("Inserted license %s (id=%s)", lic["License_ID"], license_pk)
    return license_pk


def upsert_fund(conn, fund: dict) -> int:
    row = conn.execute(
        "SELECT id FROM funds_tb WHERE Fund_Name = ?",
        (fund["Fund_Name"],),
    ).fetchone()
    sectors = _json_list(fund["Target_Sectors"])
    verified = 1 if fund["Human_Verified"] else 0

    if row:
        conn.execute(
            """
            UPDATE funds_tb
            SET Capital_Type = ?,
                Target_Sectors = ?,
                Human_Verified = ?
            WHERE id = ?
            """,
            (fund["Capital_Type"], sectors, verified, row["id"]),
        )
        log.info("Updated fund %s (id=%s)", fund["Fund_Name"], row["id"])
        return int(row["id"])

    cur = conn.execute(
        """
        INSERT INTO funds_tb (
            Fund_Name, Capital_Type, Target_Sectors, Human_Verified
        ) VALUES (?, ?, ?, ?)
        """,
        (fund["Fund_Name"], fund["Capital_Type"], sectors, verified),
    )
    fund_pk = int(cur.lastrowid)
    log.info("Inserted fund %s (id=%s)", fund["Fund_Name"], fund_pk)
    return fund_pk


def upsert_pathway(
    conn,
    *,
    fund_id: int,
    license_id: int,
    verdict: str,
    human_verified: bool,
) -> None:
    row = conn.execute(
        """
        SELECT Map_ID FROM pathways_tb
        WHERE Linked_Fund = ? AND Governing_License = ?
        """,
        (fund_id, license_id),
    ).fetchone()
    verified = 1 if human_verified else 0

    if row:
        conn.execute(
            """
            UPDATE pathways_tb
            SET Compliance_Verdict = ?, Human_Verified = ?
            WHERE Map_ID = ?
            """,
            (verdict, verified, row["Map_ID"]),
        )
        log.info(
            "Updated pathway Map_ID=%s (%s / verified=%s)",
            row["Map_ID"],
            verdict,
            human_verified,
        )
        return

    cur = conn.execute(
        """
        INSERT INTO pathways_tb (
            Linked_Fund, Governing_License, Compliance_Verdict, Human_Verified
        ) VALUES (?, ?, ?, ?)
        """,
        (fund_id, license_id, verdict, verified),
    )
    log.info(
        "Inserted pathway Map_ID=%s (%s / verified=%s)",
        cur.lastrowid,
        verdict,
        human_verified,
    )


def seed() -> None:
    db_path = init_db()
    log.info("Seeding %s", db_path)

    with get_connection(db_path) as conn:
        license_ids: dict[str, int] = {}
        for lic in LICENSES:
            license_ids[lic["License_ID"]] = upsert_license(conn, lic)

        fund_ids: dict[str, int] = {}
        for fund in FUNDS:
            fund_ids[fund["Fund_Name"]] = upsert_fund(conn, fund)

        for fund_name, license_key, verdict, verified in PATHWAYS:
            upsert_pathway(
                conn,
                fund_id=fund_ids[fund_name],
                license_id=license_ids[license_key],
                verdict=verdict,
                human_verified=verified,
            )

        conn.commit()

        pathway_count = conn.execute("SELECT COUNT(*) FROM pathways_tb").fetchone()[0]
        verified_count = conn.execute(
            "SELECT COUNT(*) FROM pathways_tb WHERE Human_Verified = 1"
        ).fetchone()[0]

    log.info(
        "Done. pathways=%s (human_verified=%s appear on Navigator)",
        pathway_count,
        verified_count,
    )


def main() -> int:
    try:
        seed()
    except Exception:
        log.exception("Seed failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

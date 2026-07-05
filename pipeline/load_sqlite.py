"""Load Anthropic-extracted license/fund JSON into local SQLite (navigator.db)."""

from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any

from database import get_connection, init_db

log = logging.getLogger(__name__)

EXPIRY_WARNING_DAYS = 30


def _parse_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return None


def compute_status(expiration: Any, current_status: str | None = None) -> str:
    if current_status == "Revoked":
        return "Revoked"
    exp_text = _parse_date(expiration)
    if exp_text is None:
        return current_status or "Active"
    exp = date.fromisoformat(exp_text)
    today = date.today()
    if exp < today:
        return "Expired"
    if exp <= today + timedelta(days=EXPIRY_WARNING_DAYS):
        return "Expiring Soon"
    return "Active"


def upsert_license(
    lic: dict[str, Any],
    *,
    source_url: str = "",
    content_hash: str = "",
    raw_snippet: str = "",
) -> int:
    """
    Insert or update a licenses_tb row from Anthropic JSON.

    Always sets Human_Verified = False for machine-loaded rows.
    Returns the row id.
    """
    init_db()
    license_id = (lic.get("License_ID") or lic.get("License Number") or "").strip()
    if not license_id:
        raise ValueError("License_ID is required")

    expiration = _parse_date(
        lic.get("Expiration_Date") or lic.get("Expiration Date")
    )
    status = compute_status(
        expiration, lic.get("Status")
    )
    activities = lic.get("Authorized_Activities") or lic.get("Authorized Activities") or []
    if isinstance(activities, str):
        activities = [a.strip() for a in activities.split(",") if a.strip()]
    exclusions = (
        lic.get("Excluded_Entities")
        or lic.get("Exclusions")
        or ""
    )
    activities_json = json.dumps(list(activities), ensure_ascii=False)
    snippet = (raw_snippet or "")[:1500]
    url = source_url if str(source_url).startswith(("http://", "https://")) else ""

    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM licenses_tb WHERE License_ID = ?",
            (license_id,),
        ).fetchone()
        if existing:
            conn.execute(
                """
                UPDATE licenses_tb
                SET Status = ?,
                    Expiration_Date = ?,
                    Authorized_Activities = ?,
                    Excluded_Entities = ?,
                    Source_URL = COALESCE(NULLIF(?, ''), Source_URL),
                    Content_Hash = COALESCE(NULLIF(?, ''), Content_Hash),
                    Raw_Snippet = COALESCE(NULLIF(?, ''), Raw_Snippet),
                    Human_Verified = 0
                WHERE id = ?
                """,
                (
                    status,
                    expiration,
                    activities_json,
                    exclusions,
                    url,
                    content_hash,
                    snippet,
                    existing["id"],
                ),
            )
            conn.commit()
            log.info("Updated license %s (id=%s, Human_Verified=False)", license_id, existing["id"])
            return int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO licenses_tb (
                License_ID, Status, Expiration_Date, Authorized_Activities,
                Excluded_Entities, Source_URL, Content_Hash, Raw_Snippet,
                Human_Verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
            """,
            (
                license_id,
                status,
                expiration,
                activities_json,
                exclusions,
                url or None,
                content_hash or None,
                snippet or None,
            ),
        )
        conn.commit()
        row_id = int(cur.lastrowid)
        log.info("Inserted license %s (id=%s, Human_Verified=False)", license_id, row_id)
        return row_id


def load_licenses(
    licenses: list[dict[str, Any]],
    *,
    source_url: str = "",
    content_hash: str = "",
    raw_snippet: str = "",
) -> list[int]:
    """Load Anthropic licenses payload into SQLite. Returns row ids."""
    ids: list[int] = []
    for lic in licenses:
        try:
            ids.append(
                upsert_license(
                    lic,
                    source_url=source_url,
                    content_hash=content_hash,
                    raw_snippet=raw_snippet,
                )
            )
        except Exception:
            log.exception("Failed to load license %s", lic)
    return ids


def _clean_amount(value: Any) -> float | None:
    """Coerce an amount to a positive float in USD, or None."""
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _sectors_json(value: Any) -> str:
    sectors = value or []
    if isinstance(sectors, str):
        sectors = [s.strip() for s in sectors.split(",") if s.strip()]
    return json.dumps(list(sectors), ensure_ascii=False)


def upsert_fund(
    fund: dict[str, Any],
    *,
    source_url: str = "",
    source_name: str = "",
    content_hash: str = "",
    raw_snippet: str = "",
    human_verified: bool = False,
    match_by: str = "Fund_Name",
) -> int:
    """
    Insert or update a funds_tb row.

    Handles both LLM-extracted funding pools and structured FTS flows
    (Donor / Recipient_Org / Amount_USD / Status). Rows are matched on
    ``match_by`` — "Fund_Name" for named pools, or "Content_Hash" for
    FTS flows so distinct transactions never collapse together.

    Returns the row id.
    """
    init_db()
    fund_name = (fund.get("Fund_Name") or fund.get("Fund Name") or "").strip()
    if not fund_name:
        raise ValueError("Fund_Name is required")

    capital_type = fund.get("Capital_Type") or fund.get("Capital Type") or ""
    sectors_json = _sectors_json(
        fund.get("Target_Sectors") or fund.get("Target Sectors")
    )
    donor = (fund.get("Donor") or "").strip()
    recipient = (fund.get("Recipient_Org") or fund.get("Recipient Org") or "").strip()
    amount = _clean_amount(fund.get("Amount_USD") or fund.get("Amount USD"))
    status = (fund.get("Status") or "").strip()
    snippet = (raw_snippet or "")[:1500]
    url = source_url if str(source_url).startswith(("http://", "https://")) else ""
    verified = 1 if human_verified else 0

    if match_by == "Content_Hash":
        match_col, match_val = "Content_Hash", (content_hash or "")
    else:
        match_col, match_val = "Fund_Name", fund_name

    with get_connection() as conn:
        existing = (
            conn.execute(
                f"SELECT id FROM funds_tb WHERE {match_col} = ?",
                (match_val,),
            ).fetchone()
            if match_val
            else None
        )
        params = (
            fund_name,
            capital_type,
            sectors_json,
            donor or None,
            recipient or None,
            amount,
            status or None,
            source_name or None,
            url or None,
            content_hash or None,
            snippet or None,
            verified,
        )
        if existing:
            conn.execute(
                """
                UPDATE funds_tb
                SET Fund_Name = ?,
                    Capital_Type = ?,
                    Target_Sectors = ?,
                    Donor = COALESCE(?, Donor),
                    Recipient_Org = COALESCE(?, Recipient_Org),
                    Amount_USD = COALESCE(?, Amount_USD),
                    Status = COALESCE(?, Status),
                    Source_Name = COALESCE(?, Source_Name),
                    Source_URL = COALESCE(?, Source_URL),
                    Content_Hash = COALESCE(?, Content_Hash),
                    Raw_Snippet = COALESCE(?, Raw_Snippet),
                    Human_Verified = ?
                WHERE id = ?
                """,
                params + (existing["id"],),
            )
            conn.commit()
            log.info(
                "Updated fund %s (id=%s, Human_Verified=%s)",
                fund_name, existing["id"], bool(verified),
            )
            return int(existing["id"])

        cur = conn.execute(
            """
            INSERT INTO funds_tb (
                Fund_Name, Capital_Type, Target_Sectors, Donor, Recipient_Org,
                Amount_USD, Status, Source_Name, Source_URL, Content_Hash,
                Raw_Snippet, Human_Verified
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            params,
        )
        conn.commit()
        row_id = int(cur.lastrowid)
        log.info(
            "Inserted fund %s (id=%s, Human_Verified=%s)",
            fund_name, row_id, bool(verified),
        )
        return row_id


def load_funds(
    funds: list[dict[str, Any]],
    *,
    source_url: str = "",
    source_name: str = "",
    content_hash: str = "",
    raw_snippet: str = "",
) -> list[int]:
    """Load LLM-extracted funds payload into SQLite (unverified). Returns ids."""
    ids: list[int] = []
    for fund in funds:
        try:
            ids.append(
                upsert_fund(
                    fund,
                    source_url=source_url,
                    source_name=source_name,
                    content_hash=content_hash,
                    raw_snippet=raw_snippet,
                    human_verified=False,
                    match_by="Fund_Name",
                )
            )
        except Exception:
            log.exception("Failed to load fund %s", fund)
    return ids


def load_flows(flows: list[dict[str, Any]]) -> list[int]:
    """
    Load structured FTS funding flows into funds_tb.

    Each flow carries its own Content_Hash (fts-<id>) so it upserts in place
    without colliding with other flows. FTS is authoritative UN data, so
    flows are stored Human_Verified = True and surface immediately.
    """
    ids: list[int] = []
    for flow in flows:
        try:
            ids.append(
                upsert_fund(
                    flow,
                    source_url=flow.get("Source_URL", ""),
                    source_name=flow.get("Source_Name", "UNOCHA FTS"),
                    content_hash=flow.get("Content_Hash", ""),
                    raw_snippet=flow.get("Raw_Snippet", ""),
                    human_verified=True,
                    match_by="Content_Hash",
                )
            )
        except Exception:
            log.exception("Failed to load FTS flow %s", flow.get("Content_Hash"))
    return ids

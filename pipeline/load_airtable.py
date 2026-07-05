"""Upsert extracted licenses and funds into Airtable (or local store)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

import config
from airtable.client import AirtableClient

log = logging.getLogger(__name__)


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value)[:10]
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def compute_status(expiration: Any, current_status: str | None = None) -> str:
    """Refresh Active / Expiring Soon / Expired from Expiration_Date."""
    if current_status == "Revoked":
        return "Revoked"
    exp = _parse_date(expiration)
    if exp is None:
        return current_status or "Active"
    today = date.today()
    if exp < today:
        return "Expired"
    if exp <= today + timedelta(days=config.EXPIRY_WARNING_DAYS):
        return "Expiring Soon"
    return "Active"


def load_licenses(
    licenses: list[dict[str, Any]],
    *,
    source_url: str,
    content_hash: str,
    raw_snippet: str = "",
    client: AirtableClient | None = None,
) -> list[dict[str, Any]]:
    """Upsert license rows. Always sets Human_Verified=False."""
    client = client or AirtableClient()
    written: list[dict[str, Any]] = []
    snippet = (raw_snippet or "")[:1500]

    for lic in licenses:
        status = compute_status(lic.get("Expiration_Date"), lic.get("Status"))
        fields = {
            "License_ID": lic["License_ID"],
            "Status": status,
            "Authorized_Activities": lic.get("Authorized_Activities") or [],
            "Excluded_Entities": lic.get("Excluded_Entities") or "",
            "Content_Hash": content_hash,
            "Raw_Snippet": snippet,
            "Human_Verified": False,
        }
        if lic.get("Expiration_Date"):
            fields["Expiration_Date"] = lic["Expiration_Date"]
        if source_url and str(source_url).startswith(("http://", "https://")):
            fields["Source_URL"] = source_url
        record = client.upsert(
            config.TABLE_LICENSES,
            fields,
            match_fields=["License_ID"],
        )
        written.append(record)
        log.info("Upserted license %s (%s)", lic["License_ID"], record.get("id"))
    return written


def load_funds(
    funds: list[dict[str, Any]],
    *,
    source_url: str,
    content_hash: str,
    raw_snippet: str = "",
    client: AirtableClient | None = None,
) -> list[dict[str, Any]]:
    """Upsert fund rows. Always sets Human_Verified=False."""
    client = client or AirtableClient()
    written: list[dict[str, Any]] = []
    snippet = (raw_snippet or "")[:1500]

    for fund in funds:
        fields = {
            "Fund_Name": fund["Fund_Name"],
            "Capital_Type": fund.get("Capital_Type", "Grant"),
            "Target_Sectors": fund.get("Target_Sectors") or [],
            "Content_Hash": content_hash,
            "Raw_Snippet": snippet,
            "Human_Verified": False,
        }
        match_fields = ["Fund_Name"]
        if source_url and str(source_url).startswith(("http://", "https://")):
            fields["Source_URL"] = source_url
            match_fields.append("Source_URL")
        record = client.upsert(
            config.TABLE_FUNDS,
            fields,
            match_fields=match_fields,
        )
        written.append(record)
        log.info("Upserted fund %s (%s)", fund["Fund_Name"], record.get("id"))
    return written

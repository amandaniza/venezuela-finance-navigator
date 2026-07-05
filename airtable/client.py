"""
Airtable database interface for the Venezuela Reconstruction Finance Navigator.

Uses the Airtable REST API via `requests` and credentials from `config.py`.
Never logs secret values.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any
from urllib.parse import quote

import requests

import config

log = logging.getLogger(__name__)

# Map scraper / LLM human-readable keys → Airtable field names (schema.md)
LICENSE_FIELD_ALIASES: dict[str, str] = {
    "License Number": "License_ID",
    "License_ID": "License_ID",
    "Status": "Status",
    "Expiration Date": "Expiration_Date",
    "Expiration_Date": "Expiration_Date",
    "Authorized Activities": "Authorized_Activities",
    "Authorized_Activities": "Authorized_Activities",
    "Exclusions": "Excluded_Entities",
    "Excluded_Entities": "Excluded_Entities",
    "Source_URL": "Source_URL",
    "Content_Hash": "Content_Hash",
    "Raw_Snippet": "Raw_Snippet",
    "Human_Verified": "Human_Verified",
}


def _serialize(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize(v) for v in value]
    if isinstance(value, dict):
        return {k: _serialize(v) for k, v in value.items()}
    return value


def normalize_license_fields(fields: dict[str, Any]) -> dict[str, Any]:
    """Normalize scraper/LLM keys to licenses_tb column names."""
    out: dict[str, Any] = {}
    for key, value in fields.items():
        canonical = LICENSE_FIELD_ALIASES.get(key, key)
        out[canonical] = value
    if "Human_Verified" not in out:
        out["Human_Verified"] = False
    # Drop empty expiration so Airtable date fields stay valid
    if not out.get("Expiration_Date"):
        out.pop("Expiration_Date", None)
    return _serialize(out)


class AirtableClient:
    """Thin REST wrapper around the configured Airtable base."""

    def __init__(self) -> None:
        api_key, base_id = config.require_airtable()
        self.api_key = api_key
        self.base_id = base_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )
        log.info("Airtable client ready for base %s", self.base_id)

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------

    def _table_url(self, table: str, record_id: str | None = None) -> str:
        encoded = quote(table, safe="")
        base = f"{config.AIRTABLE_API_URL}/{self.base_id}/{encoded}"
        if record_id:
            return f"{base}/{record_id}"
        return base

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        resp = self.session.request(
            method,
            url,
            params=params,
            json=json_body,
            timeout=config.HTTP_TIMEOUT,
        )
        if not resp.ok:
            # Do not include Authorization header material in logs
            log.error("Airtable %s %s failed (%s): %s", method, url, resp.status_code, resp.text)
            resp.raise_for_status()
        if resp.status_code == 204 or not resp.content:
            return {}
        return resp.json()

    def ping(self) -> dict[str, Any]:
        """Lightweight connectivity check against licenses_tb."""
        records = self.list_records(config.TABLE_LICENSES, max_records=1)
        return {
            "ok": True,
            "base_id": self.base_id,
            "table": config.TABLE_LICENSES,
            "sample_count": len(records),
        }

    # ------------------------------------------------------------------
    # Generic CRUD
    # ------------------------------------------------------------------

    def list_records(
        self,
        table: str,
        *,
        formula: str | None = None,
        max_records: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return all records from a table (handles pagination)."""
        params: dict[str, Any] = {"pageSize": 100}
        if formula:
            params["filterByFormula"] = formula
        if max_records is not None:
            params["maxRecords"] = max_records

        records: list[dict[str, Any]] = []
        offset: str | None = None
        url = self._table_url(table)

        while True:
            page_params = dict(params)
            if offset:
                page_params["offset"] = offset
            body = self._request("GET", url, params=page_params)
            records.extend(body.get("records", []))
            offset = body.get("offset")
            if not offset:
                break
            if max_records is not None and len(records) >= max_records:
                break

        return records

    def all_records(self, table: str) -> list[dict[str, Any]]:
        return self.list_records(table)

    def create(self, table: str, fields: dict[str, Any]) -> dict[str, Any]:
        payload = {"records": [{"fields": _serialize(fields)}], "typecast": True}
        body = self._request("POST", self._table_url(table), json_body=payload)
        records = body.get("records", [])
        if not records:
            raise RuntimeError(f"Airtable create returned no records for {table}")
        return records[0]

    def create_many(self, table: str, field_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Create up to N records (batched in groups of 10)."""
        created: list[dict[str, Any]] = []
        for i in range(0, len(field_rows), 10):
            batch = field_rows[i : i + 10]
            payload = {
                "records": [{"fields": _serialize(row)} for row in batch],
                "typecast": True,
            }
            body = self._request("POST", self._table_url(table), json_body=payload)
            created.extend(body.get("records", []))
        return created

    def update(self, table: str, record_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        payload = {"fields": _serialize(fields), "typecast": True}
        return self._request("PATCH", self._table_url(table, record_id), json_body=payload)

    def upsert(
        self,
        table: str,
        fields: dict[str, Any],
        *,
        match_fields: list[str],
    ) -> dict[str, Any]:
        """Update the first matching record, or create a new one."""
        fields = _serialize(fields)
        formula_parts: list[str] = []
        for key in match_fields:
            value = fields.get(key)
            if value is None:
                continue
            safe = str(value).replace("\\", "\\\\").replace("'", "\\'")
            formula_parts.append(f"{{{key}}}='{safe}'")

        existing: list[dict[str, Any]] = []
        if formula_parts:
            formula = (
                f"AND({','.join(formula_parts)})"
                if len(formula_parts) > 1
                else formula_parts[0]
            )
            existing = self.list_records(table, formula=formula, max_records=1)

        if existing:
            record_id = existing[0]["id"]
            return self.update(table, record_id, fields)
        return self.create(table, fields)

    def find_by_field(
        self, table: str, field: str, value: str
    ) -> dict[str, Any] | None:
        safe = str(value).replace("\\", "\\\\").replace("'", "\\'")
        rows = self.list_records(table, formula=f"{{{field}}}='{safe}'", max_records=1)
        return rows[0] if rows else None

    # ------------------------------------------------------------------
    # Domain helpers
    # ------------------------------------------------------------------

    def upsert_license(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Upsert a licenses_tb row. Machine loads set Human_Verified=False."""
        normalized = normalize_license_fields(fields)
        normalized["Human_Verified"] = False
        if not normalized.get("License_ID"):
            raise ValueError("License_ID / License Number is required")
        record = self.upsert(
            config.TABLE_LICENSES,
            normalized,
            match_fields=["License_ID"],
        )
        log.info("Upserted license %s (%s)", normalized["License_ID"], record.get("id"))
        return record

    def post_licenses(self, licenses: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Upsert many license dicts (scraper or LLM output)."""
        return [self.upsert_license(lic) for lic in licenses]

    def upsert_fund(self, fields: dict[str, Any]) -> dict[str, Any]:
        payload = _serialize(dict(fields))
        payload["Human_Verified"] = False
        if not payload.get("Fund_Name"):
            raise ValueError("Fund_Name is required")
        match = ["Fund_Name"]
        if payload.get("Source_URL"):
            match.append("Source_URL")
        record = self.upsert(config.TABLE_FUNDS, payload, match_fields=match)
        log.info("Upserted fund %s (%s)", payload["Fund_Name"], record.get("id"))
        return record

    def verified_pathways(self) -> list[dict[str, Any]]:
        """Return Human_Verified pathways with fund/license fields expanded."""
        licenses = {
            r["id"]: r["fields"] for r in self.list_records(config.TABLE_LICENSES)
        }
        funds = {r["id"]: r["fields"] for r in self.list_records(config.TABLE_FUNDS)}
        rows: list[dict[str, Any]] = []

        for pathway in self.list_records(config.TABLE_PATHWAYS):
            fields = pathway.get("fields", {})
            if not fields.get("Human_Verified"):
                continue

            fund_ids = fields.get("Linked_Fund") or []
            license_ids = fields.get("Governing_License") or []
            if isinstance(fund_ids, str):
                fund_ids = [fund_ids]
            if isinstance(license_ids, str):
                license_ids = [license_ids]

            fund = funds.get(fund_ids[0], {}) if fund_ids else {}
            license_ = licenses.get(license_ids[0], {}) if license_ids else {}

            rows.append(
                {
                    "map_id": fields.get("Map_ID") or pathway.get("id"),
                    "fund_name": fund.get("Fund_Name", ""),
                    "capital_type": fund.get("Capital_Type", ""),
                    "target_sectors": fund.get("Target_Sectors") or [],
                    "license_id": license_.get("License_ID", ""),
                    "license_status": license_.get("Status", ""),
                    "expiration_date": license_.get("Expiration_Date"),
                    "compliance_verdict": fields.get("Compliance_Verdict", ""),
                    "authorized_activities": license_.get("Authorized_Activities") or [],
                    "excluded_entities": license_.get("Excluded_Entities", ""),
                }
            )
        return rows

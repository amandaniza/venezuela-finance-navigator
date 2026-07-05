"""Create licenses_tb, funds_tb, and pathways_tb in the configured Airtable base."""

from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config

META_URL = f"https://api.airtable.com/v0/meta/bases/{config.AIRTABLE_BASE_ID}/tables"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.AIRTABLE_API_KEY}",
        "Content-Type": "application/json",
    }


def existing_tables() -> dict[str, str]:
    resp = requests.get(META_URL, headers=_headers(), timeout=30)
    resp.raise_for_status()
    return {t["name"]: t["id"] for t in resp.json().get("tables", [])}


def create_table(payload: dict) -> dict:
    resp = requests.post(META_URL, headers=_headers(), json=payload, timeout=60)
    if not resp.ok:
        print("CREATE FAILED", payload["name"], resp.status_code, resp.text[:500])
        resp.raise_for_status()
    return resp.json()


def licenses_payload() -> dict:
    return {
        "name": "licenses_tb",
        "description": "OFAC General Licenses",
        "fields": [
            {"name": "License_ID", "type": "singleLineText"},
            {
                "name": "Status",
                "type": "singleSelect",
                "options": {
                    "choices": [
                        {"name": "Active"},
                        {"name": "Expiring Soon"},
                        {"name": "Expired"},
                        {"name": "Revoked"},
                    ]
                },
            },
            {"name": "Expiration_Date", "type": "date", "options": {"dateFormat": {"name": "iso"}}},
            {
                "name": "Authorized_Activities",
                "type": "multipleSelects",
                "options": {
                    "choices": [
                        {"name": n}
                        for n in [
                            "Rubble Removal",
                            "Hospital Repair",
                            "Hospital Stabilization",
                            "Oil Extraction",
                            "Water Sanitation",
                            "WASH",
                            "Housing Repair",
                            "Infrastructure Repair",
                            "Humanitarian Aid",
                            "Energy Restoration",
                        ]
                    ]
                },
            },
            {"name": "Excluded_Entities", "type": "multilineText"},
            {"name": "Source_URL", "type": "url"},
            {"name": "Content_Hash", "type": "singleLineText"},
            {"name": "Raw_Snippet", "type": "multilineText"},
            {"name": "Human_Verified", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
        ],
    }


def funds_payload() -> dict:
    return {
        "name": "funds_tb",
        "description": "Funding sources",
        "fields": [
            {"name": "Fund_Name", "type": "singleLineText"},
            {
                "name": "Capital_Type",
                "type": "singleSelect",
                "options": {
                    "choices": [
                        {"name": "Grant"},
                        {"name": "Concessional Loan"},
                        {"name": "Commercial Debt"},
                        {"name": "Blended Finance"},
                    ]
                },
            },
            {
                "name": "Target_Sectors",
                "type": "multipleSelects",
                "options": {
                    "choices": [
                        {"name": n}
                        for n in [
                            "Healthcare",
                            "Infrastructure",
                            "WASH",
                            "Housing",
                            "Energy",
                            "Education",
                        ]
                    ]
                },
            },
            {"name": "Source_URL", "type": "url"},
            {"name": "Content_Hash", "type": "singleLineText"},
            {"name": "Raw_Snippet", "type": "multilineText"},
            {"name": "Human_Verified", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
        ],
    }


def pathways_payload(fund_table_id: str, license_table_id: str) -> dict:
    # Airtable Meta API cannot create autoNumber fields; use number instead.
    # Optionally convert Map_ID to Autonumber manually in the Airtable UI.
    return {
        "name": "pathways_tb",
        "description": "Fund ↔ license compliance map",
        "fields": [
            {
                "name": "Map_ID",
                "type": "number",
                "options": {"precision": 0},
            },
            {
                "name": "Linked_Fund",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": fund_table_id},
            },
            {
                "name": "Governing_License",
                "type": "multipleRecordLinks",
                "options": {"linkedTableId": license_table_id},
            },
            {
                "name": "Compliance_Verdict",
                "type": "singleSelect",
                "options": {
                    "choices": [
                        {"name": "Green"},
                        {"name": "Yellow"},
                        {"name": "Red"},
                    ]
                },
            },
            {
                "name": "Human_Verified",
                "type": "checkbox",
                "options": {"icon": "check", "color": "greenBright"},
            },
        ],
    }


def main() -> int:
    config.require_airtable()
    tables = existing_tables()
    print("existing", list(tables))

    if "licenses_tb" not in tables:
        lic = create_table(licenses_payload())
        tables["licenses_tb"] = lic["id"]
        print("created licenses_tb", lic["id"])
    else:
        print("licenses_tb already exists", tables["licenses_tb"])

    if "funds_tb" not in tables:
        funds = create_table(funds_payload())
        tables["funds_tb"] = funds["id"]
        print("created funds_tb", funds["id"])
    else:
        print("funds_tb already exists", tables["funds_tb"])

    if "pathways_tb" not in tables:
        path = create_table(
            pathways_payload(tables["funds_tb"], tables["licenses_tb"])
        )
        tables["pathways_tb"] = path["id"]
        print("created pathways_tb", path["id"])
    else:
        print("pathways_tb already exists", tables["pathways_tb"])

    from airtable.client import AirtableClient

    print(AirtableClient().ping())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

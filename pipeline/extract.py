"""LLM extraction of licenses_tb and funds_tb fields from raw document text."""

from __future__ import annotations

import json
import logging
from typing import Any

import config

log = logging.getLogger(__name__)

LICENSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "licenses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "License_ID": {"type": "string"},
                    "Status": {
                        "type": "string",
                        "enum": config.LICENSE_STATUSES,
                    },
                    "Expiration_Date": {"type": ["string", "null"]},
                    "Authorized_Activities": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "Excluded_Entities": {"type": "string"},
                },
                "required": [
                    "License_ID",
                    "Status",
                    "Expiration_Date",
                    "Authorized_Activities",
                    "Excluded_Entities",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["licenses"],
    "additionalProperties": False,
}

FUND_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "funds": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "Fund_Name": {"type": "string"},
                    "Capital_Type": {
                        "type": "string",
                        "enum": config.CAPITAL_TYPES,
                    },
                    "Target_Sectors": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "Donor": {"type": "string"},
                    "Recipient_Org": {"type": "string"},
                    "Amount_USD": {"type": ["number", "null"]},
                    "Status": {
                        "type": "string",
                        "enum": config.FUND_STATUSES + [""],
                    },
                },
                "required": [
                    "Fund_Name",
                    "Capital_Type",
                    "Target_Sectors",
                    "Donor",
                    "Recipient_Org",
                    "Amount_USD",
                    "Status",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["funds"],
    "additionalProperties": False,
}

LICENSE_SYSTEM = """You are a sanctions-compliance analyst.
Given raw text from a U.S. Treasury OFAC document related to Venezuela,
extract every General License into structured JSON.

You MUST identify, when present in the text:
1. The General License number exactly as written (e.g. "GL 60", "GL 46C").
2. The exact Expiration Date (convert to YYYY-MM-DD).
3. The specific authorized activities (e.g. "earthquake relief", "rubble removal",
   "hospital repair", "water sanitation").

Rules:
- Only use facts present in the text. Do not invent license IDs, dates, or activities.
- License_ID must be the General License number (e.g. "GL 60").
- Status must be one of: Active, Expiring Soon, Expired, Revoked.
- Expiration_Date must be YYYY-MM-DD or null if unknown.
- Authorized_Activities: short activity labels drawn from the document.
- Excluded_Entities: free text of banned actors; empty string if none stated.
- If no licenses can be identified, return {"licenses": []}.
"""

FUND_SYSTEM = """You are a development-finance analyst.
Given a press release or news article about relief / reconstruction funding,
extract funding pools and commitments into structured JSON.

Rules:
- Only use facts present in the text. Do not invent fund names, donors, or amounts.
- Fund_Name: official or descriptive name of the funding pool or commitment.
- Capital_Type must be one of: Grant, Concessional Loan, Commercial Debt, Blended Finance.
- Target_Sectors: choose from Healthcare, Infrastructure, WASH, Housing, Energy, Education.
- Donor: the government, agency, or institution providing the money (e.g.
  "U.S. Government", "European Commission", "CAF"); empty string if the text
  describes an open fund with no named donor.
- Recipient_Org: the organization receiving/administering the money (e.g.
  "UNICEF", "WFP", "Red Cross", "IOM"); empty string if the fund is open for
  applications rather than already allocated to a named partner.
- Amount_USD: total amount in U.S. dollars as a number (convert millions/
  billions to their full value); null if no amount is stated.
- Status must be one of: Pledged, Committed, Disbursed, or "" if unclear.
  Use Pledged for announced intentions, Committed for signed/allocated funds,
  Disbursed for money already transferred.
- If no funding pool or commitment can be identified, return {"funds": []}.
"""


def _truncate(text: str, max_chars: int = 100_000) -> str:
    if len(text) <= max_chars:
        return text
    log.warning("Truncated text from %d to %d chars", len(text), max_chars)
    return text[:max_chars]


def _openai_json(
    *,
    system: str,
    user: str,
    schema_name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    from openai import OpenAI

    if not config.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": schema_name,
                "strict": True,
                "schema": schema,
            },
        },
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty response.")
    return json.loads(content)


def _anthropic_json(
    *,
    system: str,
    user: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    import anthropic

    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set.")
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        temperature=0,
        system=system,
        messages=[
            {
                "role": "user",
                "content": (
                    f"{user}\n\nRespond with JSON only, matching this schema:\n"
                    f"{json.dumps(schema)}"
                ),
            }
        ],
    )
    text = response.content[0].text
    # Strip markdown fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        if text.endswith("```"):
            text = text[: -3]
        text = text.strip()
    return json.loads(text)


def _call_llm(
    *,
    system: str,
    user: str,
    schema_name: str,
    schema: dict[str, Any],
) -> dict[str, Any]:
    # Blueprint uses Anthropic as the sole LLM provider.
    _ = schema_name  # reserved for OpenAI structured-output path
    return _anthropic_json(system=system, user=user, schema=schema)



def extract_licenses(
    raw_text: str, *, source_url: str | None = None
) -> dict[str, Any]:
    """Return {"licenses": [licenses_tb fields...]}."""
    user = (
        f"Source URL: {source_url or 'unknown'}\n\n"
        f"--- OFAC DOCUMENT TEXT ---\n{_truncate(raw_text)}\n--- END ---"
    )
    data = _call_llm(
        system=LICENSE_SYSTEM,
        user=user,
        schema_name="licenses_tb",
        schema=LICENSE_SCHEMA,
    )
    return _validate_licenses(data)


def extract_funds(
    raw_text: str, *, source_url: str | None = None, title: str | None = None
) -> dict[str, Any]:
    """Return {"funds": [funds_tb fields...]}."""
    user = (
        f"Title: {title or 'unknown'}\n"
        f"Source URL: {source_url or 'unknown'}\n\n"
        f"--- PRESS RELEASE TEXT ---\n{_truncate(raw_text)}\n--- END ---"
    )
    data = _call_llm(
        system=FUND_SYSTEM,
        user=user,
        schema_name="funds_tb",
        schema=FUND_SCHEMA,
    )
    return _validate_funds(data)


def _validate_licenses(data: dict[str, Any]) -> dict[str, Any]:
    licenses = data.get("licenses")
    if not isinstance(licenses, list):
        raise ValueError("licenses payload missing 'licenses' array")
    cleaned = []
    for item in licenses:
        if not item.get("License_ID"):
            log.warning("Dropping license with empty License_ID")
            continue
        status = item.get("Status", "Active")
        if status not in config.LICENSE_STATUSES:
            status = "Active"
        activities = [
            a for a in (item.get("Authorized_Activities") or []) if isinstance(a, str)
        ]
        cleaned.append(
            {
                "License_ID": str(item["License_ID"]).strip(),
                "Status": status,
                "Expiration_Date": item.get("Expiration_Date"),
                "Authorized_Activities": activities,
                "Excluded_Entities": item.get("Excluded_Entities") or "",
            }
        )
    return {"licenses": cleaned}


def _clean_amount_usd(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None
    return amount if amount > 0 else None


def _validate_funds(data: dict[str, Any]) -> dict[str, Any]:
    funds = data.get("funds")
    if not isinstance(funds, list):
        raise ValueError("funds payload missing 'funds' array")
    cleaned = []
    for item in funds:
        name = (item.get("Fund_Name") or "").strip()
        if not name:
            log.warning("Dropping fund with empty Fund_Name")
            continue
        capital = item.get("Capital_Type", "Grant")
        if capital not in config.CAPITAL_TYPES:
            capital = "Grant"
        sectors = [
            s
            for s in (item.get("Target_Sectors") or [])
            if s in config.TARGET_SECTORS
        ]
        status = (item.get("Status") or "").strip()
        if status and status not in config.FUND_STATUSES:
            status = ""
        cleaned.append(
            {
                "Fund_Name": name,
                "Capital_Type": capital,
                "Target_Sectors": sectors,
                "Donor": (item.get("Donor") or "").strip(),
                "Recipient_Org": (item.get("Recipient_Org") or "").strip(),
                "Amount_USD": _clean_amount_usd(item.get("Amount_USD")),
                "Status": status,
            }
        )
    return {"funds": cleaned}

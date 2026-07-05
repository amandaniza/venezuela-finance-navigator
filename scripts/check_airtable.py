"""Connectivity check for Airtable credentials (does not print secrets)."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config


def main() -> int:
    print("anthropic_set", config.anthropic_configured())
    print("airtable_set", config.airtable_configured())
    if not config.airtable_configured():
        return 1

    headers = {"Authorization": f"Bearer {config.AIRTABLE_API_KEY}"}
    meta_url = f"https://api.airtable.com/v0/meta/bases/{config.AIRTABLE_BASE_ID}/tables"
    resp = requests.get(meta_url, headers=headers, timeout=30)
    print("meta_status", resp.status_code)
    if resp.ok:
        for table in resp.json().get("tables", []):
            fields = [f.get("name") for f in table.get("fields", [])]
            print("TABLE", table.get("name"), "| fields:", ", ".join(fields))
        return 0

    print("meta_error", resp.text[:400])
    for name in (
        config.TABLE_LICENSES,
        "Table 1",
        "Licenses",
        "OFAC Licenses",
    ):
        url = (
            f"https://api.airtable.com/v0/{config.AIRTABLE_BASE_ID}/"
            f"{quote(name, safe='')}"
        )
        probe = requests.get(
            url, headers=headers, params={"maxRecords": 1}, timeout=30
        )
        print("try", name, probe.status_code)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

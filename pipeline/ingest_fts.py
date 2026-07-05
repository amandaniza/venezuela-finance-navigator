"""
Ingest humanitarian funding flows from the UNOCHA Financial Tracking Service.

The FTS public API (https://api.hpc.tools) publishes every reported funding
flow into a country for a given year: who gave (Donor), who received
(Recipient Organization), how much (Amount USD), and the lifecycle status
(pledge / commitment / paid → Pledged / Committed / Disbursed).

We pull all *incoming* flows for the Venezuela 2026 appeal, normalise them
into funds_tb rows, and mark those tied to the earthquake response. Unlike
the LLM-scraped funds, FTS data is structured and authoritative, so flows
are loaded Human_Verified = True and appear on the Navigator immediately.

Usage:
    python -m pipeline.ingest_fts            # ingest into SQLite
    python -m pipeline.ingest_fts --dry-run  # fetch + print, no writes
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config

log = logging.getLogger(__name__)

# Cap pagination so a misbehaving API can never spin forever.
_MAX_PAGES = 50
_PAGE_LIMIT = 1000


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": config.USER_AGENT,
            "Accept": "application/json",
        }
    )
    return session


def _flow_endpoint() -> str:
    return (
        f"{config.FTS_API_BASE}/fts/flow"
        f"?countryISO3={config.FTS_COUNTRY_ISO3}"
        f"&year={config.FTS_APPEAL_YEAR}"
        f"&limit={_PAGE_LIMIT}"
    )


def fetch_raw_flows(session: requests.Session | None = None) -> list[dict[str, Any]]:
    """Return every raw FTS flow for the configured country/year (paginated)."""
    sess = session or _session()
    url: str | None = _flow_endpoint()
    flows: list[dict[str, Any]] = []
    pages = 0

    while url and pages < _MAX_PAGES:
        log.info("FTS: fetching %s", url)
        resp = sess.get(url, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or {}
        page_flows = data.get("flows") or []
        flows.extend(page_flows)
        meta = payload.get("meta") or {}
        url = meta.get("nextLink")
        pages += 1

    log.info("FTS: %d raw flow(s) across %d page(s)", len(flows), pages)
    return flows


def _first_org(objects: list[dict[str, Any]]) -> str:
    """Name of the first Organization in an FTS source/destination list."""
    for obj in objects or []:
        if obj.get("type") == "Organization" and obj.get("name"):
            return str(obj["name"]).strip()
    return ""


def _is_earthquake_related(flow: dict[str, Any]) -> bool:
    blob_parts = [flow.get("description") or ""]
    blob_parts += flow.get("keywords") or []
    blob = " ".join(str(p) for p in blob_parts).lower()
    return any(k in blob for k in config.FTS_EARTHQUAKE_KEYWORDS)


def _normalise_flow(flow: dict[str, Any]) -> dict[str, Any] | None:
    """Turn one raw FTS flow into a funds_tb-shaped record, or None to skip."""
    # Only money actually flowing into Venezuela.
    if flow.get("boundary") not in (None, "incoming"):
        return None
    amount = flow.get("amountUSD")
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        amount = 0.0
    if amount <= 0:  # drop corrections/reversals and zero-value rows
        return None

    donor = _first_org(flow.get("sourceObjects", []))
    recipient = _first_org(flow.get("destinationObjects", []))
    if not donor and not recipient:
        return None

    raw_status = str(flow.get("status") or "").lower()
    status = config.FTS_STATUS_MAP.get(raw_status, raw_status.title() or "Committed")

    flow_id = flow.get("id")
    description = (flow.get("description") or "").strip()
    fund_name = description[:180] if description else (
        f"{donor or 'Unknown donor'} → {recipient or 'Unnamed recipient'}"
    )

    return {
        "Fund_Name": fund_name,
        "Capital_Type": "Grant",  # FTS humanitarian contributions are grants
        "Target_Sectors": [],
        "Donor": donor,
        "Recipient_Org": recipient,
        "Amount_USD": amount,
        "Status": status,
        "Source_Name": "UNOCHA FTS",
        "Source_URL": f"https://fts.unocha.org/flows/{flow_id}" if flow_id else "",
        "Content_Hash": f"fts-{flow_id}",
        "Raw_Snippet": description[:1500],
        "earthquake_related": _is_earthquake_related(flow),
        "budget_year": flow.get("budgetYear"),
    }


def fetch_fts_flows(
    *,
    earthquake_only: bool = False,
    session: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch and normalise FTS flows for the Venezuela appeal year.

    Set ``earthquake_only`` to keep just the flows whose description or
    keywords reference the seismic response.
    """
    raw = fetch_raw_flows(session)
    records: list[dict[str, Any]] = []
    for flow in raw:
        record = _normalise_flow(flow)
        if record is None:
            continue
        if earthquake_only and not record["earthquake_related"]:
            continue
        records.append(record)
    log.info(
        "FTS: %d usable flow(s)%s",
        len(records),
        " (earthquake-related)" if earthquake_only else "",
    )
    return records


def ingest_fts(*, earthquake_only: bool = False, dry_run: bool = False) -> dict[str, Any]:
    """Fetch FTS flows and load them into funds_tb. Returns a summary dict."""
    try:
        records = fetch_fts_flows(earthquake_only=earthquake_only)
    except requests.RequestException as exc:
        log.error("FTS fetch failed: %s", exc)
        return {"fetched": 0, "loaded_ids": [], "total_usd": 0.0, "error": str(exc)}

    total_usd = sum(r["Amount_USD"] for r in records)
    eq_count = sum(1 for r in records if r["earthquake_related"])

    if dry_run:
        log.info("Dry-run: skipping SQLite writes for %d flow(s)", len(records))
        return {
            "fetched": len(records),
            "earthquake_related": eq_count,
            "loaded_ids": [],
            "total_usd": total_usd,
        }

    from pipeline.load_sqlite import load_flows

    loaded_ids = load_flows(records)
    return {
        "fetched": len(records),
        "earthquake_related": eq_count,
        "loaded_ids": loaded_ids,
        "total_usd": total_usd,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest UNOCHA FTS Venezuela flows")
    parser.add_argument(
        "--earthquake-only",
        action="store_true",
        help="Keep only flows referencing the earthquake response",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and summarise without writing to SQLite",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    summary = ingest_fts(
        earthquake_only=args.earthquake_only, dry_run=args.dry_run
    )
    log.info(
        "FTS ingest: fetched=%s loaded=%s total_usd=%.0f",
        summary.get("fetched"),
        len(summary.get("loaded_ids") or []),
        summary.get("total_usd") or 0.0,
    )
    return 0 if "error" not in summary else 1


if __name__ == "__main__":
    raise SystemExit(main())

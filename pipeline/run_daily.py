"""
Daily orchestrator: scrape → extract → load.

Usage (from repo root):
    python pipeline/run_daily.py
    python pipeline/run_daily.py --force-all
    python pipeline/run_daily.py --dry-run
    python pipeline/run_daily.py --ofac-only
    python pipeline/run_daily.py --funds-only
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure repo root is on sys.path when run as a script
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from pipeline.extract import extract_funds, extract_licenses
from pipeline.load_airtable import load_funds, load_licenses
from pipeline.scrape import scrape_fund_portals, scrape_ofac

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("run_daily")


def _write_artifact(name: str, payload: dict) -> Path:
    config.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    path = config.EXTRACTED_DIR / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def process_ofac(*, force_all: bool, dry_run: bool) -> list[dict]:
    docs = scrape_ofac(force_all=force_all)
    results = []
    for doc in docs:
        log.info("OFAC doc: %s", doc["title"])
        if dry_run or not config.llm_configured():
            if not config.llm_configured() and not dry_run:
                log.warning("LLM not configured; skipping extraction for %s", doc["id"])
            licenses_payload = {"licenses": []}
        else:
            try:
                licenses_payload = extract_licenses(
                    doc["text"], source_url=doc.get("pdf_url") or doc["url"]
                )
            except Exception:
                log.exception("License extraction failed for %s", doc["id"])
                continue

        source_url = doc.get("pdf_url") or doc["url"]
        record = {
            "source_type": "ofac",
            "title": doc["title"],
            "url": doc["url"],
            "pdf_url": doc.get("pdf_url"),
            "content_hash": doc["content_hash"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "licenses_tb": licenses_payload,
        }
        _write_artifact(f"ofac_{doc['id']}.json", record)

        if not dry_run and licenses_payload.get("licenses"):
            load_licenses(
                licenses_payload["licenses"],
                source_url=source_url,
                content_hash=doc["content_hash"],
                raw_snippet=doc["text"][:1500],
            )
        results.append(record)
    return results


def process_funds(*, force_all: bool, dry_run: bool) -> list[dict]:
    docs = scrape_fund_portals(force_all=force_all)
    results = []
    for doc in docs:
        log.info("Fund doc: %s", doc["title"][:80])
        if dry_run or not config.llm_configured():
            if not config.llm_configured() and not dry_run:
                log.warning("LLM not configured; skipping extraction for %s", doc["id"])
            funds_payload = {"funds": []}
        else:
            try:
                funds_payload = extract_funds(
                    doc["text"], source_url=doc["url"], title=doc["title"]
                )
            except Exception:
                log.exception("Fund extraction failed for %s", doc["id"])
                continue

        record = {
            "source_type": "fund",
            "title": doc["title"],
            "url": doc["url"],
            "content_hash": doc["content_hash"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "funds_tb": funds_payload,
        }
        _write_artifact(f"fund_{doc['id']}.json", record)

        if not dry_run and funds_payload.get("funds"):
            load_funds(
                funds_payload["funds"],
                source_url=doc["url"],
                content_hash=doc["content_hash"],
                raw_snippet=doc["text"][:1500],
            )
        results.append(record)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Daily scrape → LLM extract → Airtable load"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-process documents even if already seen",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape only; skip LLM and Airtable writes",
    )
    parser.add_argument("--ofac-only", action="store_true")
    parser.add_argument("--funds-only", action="store_true")
    args = parser.parse_args(argv)

    do_ofac = not args.funds_only
    do_funds = not args.ofac_only

    summary: dict = {"ofac": [], "funds": []}
    try:
        if do_ofac:
            summary["ofac"] = process_ofac(
                force_all=args.force_all, dry_run=args.dry_run
            )
        if do_funds:
            summary["funds"] = process_funds(
                force_all=args.force_all, dry_run=args.dry_run
            )
    except Exception:
        log.exception("Daily pipeline failed")
        return 1

    print(
        json.dumps(
            {
                "ofac_docs": len(summary["ofac"]),
                "fund_docs": len(summary["funds"]),
                "ofac": [
                    {
                        "title": r["title"],
                        "licenses": r["licenses_tb"].get("licenses", []),
                    }
                    for r in summary["ofac"]
                ],
                "funds": [
                    {
                        "title": r["title"],
                        "funds": r["funds_tb"].get("funds", []),
                    }
                    for r in summary["funds"]
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

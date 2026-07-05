"""
Master pipeline: OFAC + fund-portal scrape + UNOCHA FTS API
→ Anthropic extract → SQLite load.

Three ingestion sources, all landing in the SQLite navigator DB:
  1. OFAC Recent Actions  → licenses_tb  (Playwright/requests + LLM)
  2. CAF/IDB/State/ECHO   → funds_tb     (Playwright + LLM)
  3. UNOCHA FTS API       → funds_tb     (structured donor→recipient flows)

Usage (from repo root):
    python run_pipeline.py
    python run_pipeline.py --force-all
    python run_pipeline.py --dry-run
    python run_pipeline.py --ofac-only
    python run_pipeline.py --funds-only
    python run_pipeline.py --fts-only
    python run_pipeline.py --no-fts
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from database import init_db
from pipeline.extract import extract_funds, extract_licenses
from pipeline.ingest_fts import ingest_fts
from pipeline.load_sqlite import load_funds, load_licenses
from pipeline.scrape import scrape_fund_portals, scrape_ofac

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("run_pipeline")


def _require_anthropic() -> None:
    if not config.anthropic_configured():
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env before running."
        )


def _write_artifact(name: str, payload: dict) -> Path:
    config.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    path = config.EXTRACTED_DIR / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def process_ofac(*, force_all: bool = False, dry_run: bool = False) -> list[dict]:
    """Scrape OFAC Recent Actions → extract licenses → load into SQLite."""
    log.info("OFAC — Scrape Recent Actions (Venezuela, 2026)")
    documents = scrape_ofac(force_all=force_all)
    log.info("OFAC: %d document(s)", len(documents))

    results: list[dict] = []
    for doc in documents:
        log.info("OFAC — Extract licenses: %s", doc["title"])
        source_url = doc.get("pdf_url") or doc["url"]

        if dry_run:
            licenses: list[dict] = []
            log.info("Dry-run: skipping Anthropic")
        else:
            _require_anthropic()
            try:
                payload = extract_licenses(doc["text"], source_url=source_url)
                licenses = payload.get("licenses") or []
            except Exception:
                log.exception("Extraction failed for %s", doc["id"])
                continue

        record = {
            "source_type": "ofac",
            "title": doc["title"],
            "url": doc["url"],
            "pdf_url": doc.get("pdf_url"),
            "content_hash": doc["content_hash"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "licenses": licenses,
            "loaded_ids": [],
        }

        if not dry_run and licenses:
            log.info("OFAC — Load %d license(s) into SQLite", len(licenses))
            record["loaded_ids"] = load_licenses(
                licenses,
                source_url=source_url,
                content_hash=doc["content_hash"],
                raw_snippet=doc["text"][:1500],
            )
        elif not licenses:
            log.warning("No licenses extracted from %s", doc["title"])

        out = _write_artifact(f"pipeline_{doc['id']}.json", record)
        log.info("Wrote %s", out)
        results.append(record)
    return results


def process_funds(*, force_all: bool = False, dry_run: bool = False) -> list[dict]:
    """Scrape CAF/IDB portals (Playwright) → extract funds → load into SQLite."""
    log.info("Funds — Scrape CAF/IDB portals (headless browser)")
    documents = scrape_fund_portals(force_all=force_all)
    log.info("Funds: %d document(s)", len(documents))

    results: list[dict] = []
    for doc in documents:
        log.info("Funds — Extract funds: %s", doc["title"][:80])

        if dry_run:
            funds: list[dict] = []
            log.info("Dry-run: skipping Anthropic")
        else:
            _require_anthropic()
            try:
                payload = extract_funds(
                    doc["text"], source_url=doc["url"], title=doc["title"]
                )
                funds = payload.get("funds") or []
            except Exception:
                log.exception("Extraction failed for %s", doc["id"])
                continue

        record = {
            "source_type": "fund",
            "source_name": doc.get("source_name"),
            "title": doc["title"],
            "url": doc["url"],
            "content_hash": doc["content_hash"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "funds": funds,
            "loaded_ids": [],
        }

        if not dry_run and funds:
            log.info("Funds — Load %d fund(s) into SQLite", len(funds))
            record["loaded_ids"] = load_funds(
                funds,
                source_url=doc["url"],
                source_name=doc.get("source_name") or "",
                content_hash=doc["content_hash"],
                raw_snippet=doc["text"][:1500],
            )
        elif not funds:
            log.warning("No funds extracted from %s", doc["title"])

        out = _write_artifact(f"fund_{doc['id']}.json", record)
        log.info("Wrote %s", out)
        results.append(record)
    return results


def process_fts(*, dry_run: bool = False) -> dict:
    """Ingest UNOCHA FTS donor→recipient flows into funds_tb (verified)."""
    log.info("FTS — Ingest UNOCHA flows for %s %s",
             config.FTS_COUNTRY_ISO3, config.FTS_APPEAL_YEAR)
    summary = ingest_fts(dry_run=dry_run)
    log.info(
        "FTS: fetched=%s loaded=%s total_usd=%.0f",
        summary.get("fetched"),
        len(summary.get("loaded_ids") or []),
        summary.get("total_usd") or 0.0,
    )
    return summary


def run(
    *,
    force_all: bool = False,
    dry_run: bool = False,
    do_ofac: bool = True,
    do_funds: bool = True,
    do_fts: bool = True,
) -> dict:
    init_db()
    config.EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    ofac_results = (
        process_ofac(force_all=force_all, dry_run=dry_run) if do_ofac else []
    )
    fund_results = (
        process_funds(force_all=force_all, dry_run=dry_run) if do_funds else []
    )
    fts_summary = process_fts(dry_run=dry_run) if do_fts else {}

    return {
        "ofac_documents": len(ofac_results),
        "fund_documents": len(fund_results),
        "fts_flows": fts_summary.get("fetched", 0),
        "licenses_loaded": sum(
            len(r.get("loaded_ids") or []) for r in ofac_results
        ),
        "funds_loaded": sum(
            len(r.get("loaded_ids") or []) for r in fund_results
        ),
        "fts_loaded": len(fts_summary.get("loaded_ids") or []),
        "fts_total_usd": fts_summary.get("total_usd", 0.0),
        "results": {
            "ofac": [
                {
                    "title": r["title"],
                    "licenses": r["licenses"],
                    "loaded_ids": r["loaded_ids"],
                }
                for r in ofac_results
            ],
            "funds": [
                {
                    "title": r["title"],
                    "funds": r["funds"],
                    "loaded_ids": r["loaded_ids"],
                }
                for r in fund_results
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OFAC + fund-portal scrape → Anthropic extract → SQLite load"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-process entries even if already seen",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape only; skip Anthropic and SQLite writes",
    )
    parser.add_argument(
        "--ofac-only", action="store_true",
        help="Run only the OFAC scraper (skip funds + FTS)",
    )
    parser.add_argument(
        "--funds-only", action="store_true",
        help="Run only the fund-portal scraper (skip OFAC + FTS)",
    )
    parser.add_argument(
        "--fts-only", action="store_true",
        help="Run only the UNOCHA FTS ingest (skip OFAC + funds)",
    )
    parser.add_argument(
        "--no-fts", action="store_true", help="Skip the UNOCHA FTS ingest",
    )
    args = parser.parse_args(argv)

    only = args.ofac_only or args.funds_only or args.fts_only
    if only:
        do_ofac = args.ofac_only
        do_funds = args.funds_only
        do_fts = args.fts_only
    else:
        do_ofac = do_funds = True
        do_fts = not args.no_fts

    try:
        summary = run(
            force_all=args.force_all,
            dry_run=args.dry_run,
            do_ofac=do_ofac,
            do_funds=do_funds,
            do_fts=do_fts,
        )
    except Exception:
        log.exception("Pipeline failed")
        return 1

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

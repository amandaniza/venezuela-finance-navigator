"""
OFAC Recent Actions scraper → Anthropic extraction → Airtable load.

Monitors the U.S. Treasury OFAC Recent Actions page for Venezuela updates,
downloads linked PDFs, extracts text with pypdf, asks Claude to structure
license fields, and POSTs records into Airtable.

Usage:
    python scraper.py
    python scraper.py --force-all
    python scraper.py --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import anthropic
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

OFAC_RECENT_ACTIONS_URL = "https://ofac.treasury.gov/recent-actions"
KEYWORD = "Venezuela"
ANTHROPIC_MODEL = "claude-3-5-sonnet-20240620"

PDF_DIR = ROOT / "data" / "raw" / "pdfs"
STATE_PATH = ROOT / "data" / "state" / "seen_scraper.json"
OUTPUT_DIR = ROOT / "data" / "extracted"

ACTION_PATH_RE = re.compile(r"/recent-actions/\d{8}", re.IGNORECASE)
MEDIA_DOWNLOAD_RE = re.compile(r"/media/\d+/download", re.IGNORECASE)

# OFAC table fields (Airtable column names)
OFAC_FIELDS = [
    "License Number",
    "Status",
    "Expiration Date",
    "Authorized Activities",
    "Exclusions",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scraper")


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_seen() -> set[str]:
    if not STATE_PATH.exists():
        return set()
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read state (%s); starting fresh.", exc)
        return set()


def save_seen(seen: set[str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "seen_ids": sorted(seen),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def action_id(url: str, title: str) -> str:
    raw = f"{url.strip()}|{title.strip()}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------------
# OFAC scrape + PDF download + text extract
# ---------------------------------------------------------------------------

def session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (compatible; VenezuelaFinanceNavigator/1.0; "
                "+research; compliance monitoring)"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
    )
    return s


def is_pdf_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return path.endswith(".pdf") or bool(MEDIA_DOWNLOAD_RE.search(path)) or "pdf" in path


def is_recent_action_url(url: str) -> bool:
    return bool(ACTION_PATH_RE.search(urlparse(url).path))


def parse_recent_actions(html: str, base_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    entries: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#"):
            continue
        full = urljoin(base_url, href)
        if not is_recent_action_url(full) or full in seen_urls:
            continue
        seen_urls.add(full)

        title = a.get_text(" ", strip=True) or full
        parent = a.find_parent(["li", "article", "tr", "div"])
        context = " ".join(parent.stripped_strings) if parent else title
        pdf_urls: list[str] = []
        if is_pdf_url(full):
            pdf_urls.append(full)
        if parent:
            for sibling in parent.find_all("a", href=True):
                sibling_url = urljoin(base_url, sibling["href"].strip())
                if is_pdf_url(sibling_url):
                    pdf_urls.append(sibling_url)

        entries.append(
            {
                "id": action_id(full, title),
                "title": title,
                "url": full,
                "text": context,
                "pdf_urls": list(dict.fromkeys(pdf_urls)),
            }
        )
    return entries


def mentions_venezuela(entry: dict[str, Any]) -> bool:
    blob = f"{entry.get('title', '')} {entry.get('text', '')}"
    return KEYWORD.lower() in blob.lower()


def collect_pdf_urls(entry_url: str, sess: requests.Session) -> list[str]:
    if is_pdf_url(entry_url):
        return [entry_url]
    try:
        resp = sess.get(entry_url, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.warning("Failed to open %s: %s", entry_url, exc)
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    return list(
        dict.fromkeys(
            urljoin(entry_url, a["href"].strip())
            for a in soup.find_all("a", href=True)
            if is_pdf_url(urljoin(entry_url, a["href"].strip()))
        )
    )


def download_pdf(url: str, sess: requests.Session) -> Path | None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    existing = list(PDF_DIR.glob(f"{digest}_*.pdf"))
    if existing and existing[0].stat().st_size > 0:
        log.info("PDF already on disk: %s", existing[0].name)
        return existing[0]

    try:
        resp = sess.get(url, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("Download failed for %s: %s", url, exc)
        return None

    body = resp.content
    if body[:4] != b"%PDF" and "pdf" not in resp.headers.get("Content-Type", "").lower():
        if not is_pdf_url(url):
            log.warning("Skipping non-PDF response from %s", url)
            return None

    disposition = resp.headers.get("Content-Disposition", "")
    match = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposition, re.I)
    if match:
        name = Path(match.group(1).strip()).name
    else:
        name = Path(urlparse(url).path).name or "document.pdf"
        if name.lower() == "download":
            name = "document.pdf"
    name = re.sub(r"[^\w.\-]+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"

    dest = PDF_DIR / f"{digest}_{name}"
    dest.write_bytes(body)
    log.info("Downloaded %s (%d bytes)", dest.name, len(body))
    return dest


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract text from a PDF using pypdf."""
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            pages.append(page.extract_text() or "")
        except Exception as exc:  # noqa: BLE001
            log.warning("Page %d of %s failed: %s", i, pdf_path.name, exc)
            pages.append("")
    return "\n\n".join(pages).strip()


def scrape_venezuela_updates(*, force_all: bool = False) -> list[dict[str, Any]]:
    """
    Find new Venezuela-related OFAC actions, download PDFs, extract text.

    Returns a list of dicts with keys: id, title, url, pdf_url, pdf_path, text.
    """
    sess = session()
    log.info("Fetching %s", OFAC_RECENT_ACTIONS_URL)
    resp = sess.get(OFAC_RECENT_ACTIONS_URL, timeout=60)
    resp.raise_for_status()

    entries = [e for e in parse_recent_actions(resp.text, OFAC_RECENT_ACTIONS_URL) if mentions_venezuela(e)]
    log.info("%d Venezuela-related entr(y/ies)", len(entries))

    seen = set() if force_all else load_seen()
    documents: list[dict[str, Any]] = []

    for entry in entries:
        if entry["id"] in seen:
            continue

        pdf_urls = list(entry.get("pdf_urls") or []) or collect_pdf_urls(entry["url"], sess)
        if not pdf_urls:
            log.warning("No PDFs for %s", entry["url"])
            seen.add(entry["id"])
            continue

        for pdf_url in pdf_urls:
            pdf_path = download_pdf(pdf_url, sess)
            if pdf_path is None:
                continue
            text = extract_text_from_pdf(pdf_path)
            if not text:
                log.warning("No extractable text in %s", pdf_path.name)
                continue
            documents.append(
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "pdf_url": pdf_url,
                    "pdf_path": str(pdf_path),
                    "text": text,
                }
            )
            log.info("Extracted %d chars from %s", len(text), pdf_path.name)

        seen.add(entry["id"])

    save_seen(seen)
    return documents


# ---------------------------------------------------------------------------
# Anthropic: raw text → OFAC table JSON
# ---------------------------------------------------------------------------

EXTRACTION_SYSTEM = """You are a sanctions-compliance analyst.
Given raw text from a U.S. Treasury OFAC document related to Venezuela,
extract every General License into structured JSON.

Return ONLY valid JSON of the form:
{
  "licenses": [
    {
      "License Number": "GL 60",
      "Status": "Active",
      "Expiration Date": "2026-10-23",
      "Authorized Activities": ["Hospital Repair", "Rubble Removal"],
      "Exclusions": "PdVSA, Minerven"
    }
  ]
}

Rules:
- Only use facts present in the text. Do not invent license numbers or dates.
- Status must be one of: Active, Expiring Soon, Expired, Revoked.
- Expiration Date must be YYYY-MM-DD, or null if unknown.
- Authorized Activities is an array of short activity labels.
- Exclusions is free text of banned actors; use an empty string if none stated.
- If no licenses can be identified, return {"licenses": []}.
"""


def extract_licenses_with_anthropic(
    raw_text: str,
    *,
    source_url: str | None = None,
) -> list[dict[str, Any]]:
    """
    Send PDF text to Claude and return license dicts matching the OFAC table:

        License Number, Status, Expiration Date, Authorized Activities, Exclusions
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set in .env")

    client = anthropic.Anthropic(api_key=api_key)
    max_chars = 100_000
    text_for_model = raw_text[:max_chars]

    user_content = (
        f"Source URL: {source_url or 'unknown'}\n\n"
        f"--- OFAC DOCUMENT TEXT ---\n{text_for_model}\n--- END ---"
    )

    message = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=4096,
        temperature=0,
        system=EXTRACTION_SYSTEM,
        messages=[{"role": "user", "content": user_content}],
    )

    content = message.content[0].text.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[: -3]
        content = content.strip()

    data = json.loads(content)
    licenses = data.get("licenses", [])
    if not isinstance(licenses, list):
        raise ValueError("Claude response missing 'licenses' array")

    cleaned: list[dict[str, Any]] = []
    for item in licenses:
        number = (item.get("License Number") or item.get("License_ID") or "").strip()
        if not number:
            continue
        activities = item.get("Authorized Activities") or item.get("Authorized_Activities") or []
        if isinstance(activities, str):
            activities = [a.strip() for a in activities.split(",") if a.strip()]
        cleaned.append(
            {
                "License Number": number,
                "Status": item.get("Status") or "Active",
                "Expiration Date": item.get("Expiration Date")
                or item.get("Expiration_Date"),
                "Authorized Activities": activities,
                "Exclusions": item.get("Exclusions")
                or item.get("Excluded_Entities")
                or "",
            }
        )
    return cleaned


# ---------------------------------------------------------------------------
# Airtable: POST structured JSON via requests
# ---------------------------------------------------------------------------

def post_licenses_to_airtable(licenses: list[dict[str, Any]]) -> dict[str, Any]:
    """
    POST license records into the Airtable base using environment variables:

        AIRTABLE_API_KEY
        AIRTABLE_BASE_ID
        AIRTABLE_TABLE_LICENSES  (default: licenses_tb)
    """
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    table = os.getenv("AIRTABLE_TABLE_LICENSES", "licenses_tb")

    if not api_key or not base_id:
        raise RuntimeError(
            "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in .env"
        )

    url = f"https://api.airtable.com/v0/{base_id}/{requests.utils.quote(table, safe='')}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Airtable accepts max 10 records per create request
    created: list[dict[str, Any]] = []
    for i in range(0, len(licenses), 10):
        batch = licenses[i : i + 10]
        records = []
        for lic in batch:
            fields = {
                "License Number": lic["License Number"],
                "Status": lic.get("Status") or "Active",
                "Expiration Date": lic.get("Expiration Date"),
                "Authorized Activities": lic.get("Authorized Activities") or [],
                "Exclusions": lic.get("Exclusions") or "",
                "Human_Verified": False,
            }
            # Drop null expiration so Airtable date fields stay valid
            if not fields["Expiration Date"]:
                fields.pop("Expiration Date")
            records.append({"fields": fields})

        payload = {"records": records, "typecast": True}
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        if not resp.ok:
            log.error("Airtable error %s: %s", resp.status_code, resp.text)
            resp.raise_for_status()
        body = resp.json()
        created.extend(body.get("records", []))
        log.info("Posted %d license(s) to Airtable", len(body.get("records", [])))

    return {"records": created}


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run(*, force_all: bool = False, dry_run: bool = False) -> list[dict[str, Any]]:
    documents = scrape_venezuela_updates(force_all=force_all)
    if not documents:
        log.info("No new Venezuela documents to process.")
        return []

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    for doc in documents:
        log.info("Processing: %s", doc["title"])
        if dry_run:
            licenses: list[dict[str, Any]] = []
        else:
            licenses = extract_licenses_with_anthropic(
                doc["text"], source_url=doc.get("pdf_url") or doc["url"]
            )
            log.info("Extracted %d license(s)", len(licenses))

        record = {
            "action_id": doc["id"],
            "title": doc["title"],
            "url": doc["url"],
            "pdf_url": doc.get("pdf_url"),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "licenses": licenses,
        }

        out_path = OUTPUT_DIR / f"scraper_{doc['id']}.json"
        out_path.write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log.info("Wrote %s", out_path)

        if not dry_run and licenses:
            airtable_result = post_licenses_to_airtable(licenses)
            record["airtable"] = {
                "posted": len(airtable_result.get("records", [])),
                "ids": [r.get("id") for r in airtable_result.get("records", [])],
            }

        results.append(record)

    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="OFAC Venezuela scraper → Anthropic → Airtable"
    )
    parser.add_argument(
        "--force-all",
        action="store_true",
        help="Re-process all Venezuela entries, ignoring seen state",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and extract PDF text only; skip Anthropic and Airtable",
    )
    args = parser.parse_args(argv)

    try:
        results = run(force_all=args.force_all, dry_run=args.dry_run)
    except Exception:
        log.exception("Scraper failed")
        return 1

    print(
        json.dumps(
            [
                {
                    "title": r["title"],
                    "pdf_url": r.get("pdf_url"),
                    "licenses": r.get("licenses", []),
                    "airtable": r.get("airtable"),
                }
                for r in results
            ],
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Secure configuration loader for the Venezuela Reconstruction Finance Navigator.

Reads secrets from `.env` via python-dotenv. Never hard-code API keys.
Required for the live pipeline:

    ANTHROPIC_API_KEY
    AIRTABLE_API_KEY
    AIRTABLE_BASE_ID
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent

# Load .env from the project root only (does not override existing OS env vars).
load_dotenv(ROOT / ".env", override=False)


def _env(name: str, default: str = "") -> str:
    """Return a stripped environment variable, or default if unset/blank."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip()


# ---------------------------------------------------------------------------
# Secrets (never commit real values)
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: str = _env("ANTHROPIC_API_KEY")
AIRTABLE_API_KEY: str = _env("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID: str = _env("AIRTABLE_BASE_ID")

# ---------------------------------------------------------------------------
# Optional overrides
# ---------------------------------------------------------------------------

ANTHROPIC_MODEL: str = _env("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
AIRTABLE_TABLE_LICENSES: str = _env("AIRTABLE_TABLE_LICENSES", "licenses_tb")
AIRTABLE_TABLE_FUNDS: str = _env("AIRTABLE_TABLE_FUNDS", "funds_tb")
AIRTABLE_TABLE_PATHWAYS: str = _env("AIRTABLE_TABLE_PATHWAYS", "pathways_tb")

# Back-compat aliases used by existing modules
TABLE_LICENSES = AIRTABLE_TABLE_LICENSES
TABLE_FUNDS = AIRTABLE_TABLE_FUNDS
TABLE_PATHWAYS = AIRTABLE_TABLE_PATHWAYS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PDF_DIR = RAW_DIR / "pdfs"
HTML_DIR = RAW_DIR / "html"
STATE_DIR = DATA_DIR / "state"
EXTRACTED_DIR = DATA_DIR / "extracted"
SEED_DIR = DATA_DIR / "seed"
LOCAL_DB_PATH = SEED_DIR / "local_db.json"

# ---------------------------------------------------------------------------
# Pipeline constants
# ---------------------------------------------------------------------------

OFAC_RECENT_ACTIONS_URL = "https://ofac.treasury.gov/recent-actions"
VENEZUELA_KEYWORD = "Venezuela"
USER_AGENT = "VenezuelaFinanceNavigator/1.0 (+research; compliance monitoring)"
EXPIRY_WARNING_DAYS = 30
HTTP_TIMEOUT = 60
AIRTABLE_API_URL = "https://api.airtable.com/v0"

# ---------------------------------------------------------------------------
# UNOCHA Financial Tracking Service (FTS) — public API
# https://api.hpc.tools/  (no auth required)
# ---------------------------------------------------------------------------

FTS_API_BASE = "https://api.hpc.tools/v1/public"
FTS_COUNTRY_ISO3 = "VEN"
FTS_APPEAL_YEAR = "2026"
# Keywords used to flag flows tied to the 2026 earthquake response. FTS does
# not yet publish a dedicated earthquake plan, so we ingest all incoming
# country flows for the appeal year and tag the earthquake-related ones.
FTS_EARTHQUAKE_KEYWORDS = ["earthquake", "seismic", "terremoto", "sismo"]

# ---------------------------------------------------------------------------
# Funding directory (navigator_funding_seed.json) + context figures
# ---------------------------------------------------------------------------

FUNDING_SEED_PATH = ROOT / "navigator_funding_seed.json"
FUNDING_LAST_CHECKED = "2026-07-04"

# Reference context figures (from the seed meta block). Used for hero context.
UN_RECONSTRUCTION_ESTIMATE_USD = 6_700_000_000
PEOPLE_IN_NEED_EARTHQUAKE = 1_800_000
PEOPLE_IN_NEED_PRE_QUAKE = 7_900_000
GL60_ISSUED = "2026-06-25"
GL60_EXPIRES = "2026-10-23"
# OCHA revised response plan lands the week of this date (leave a UI slot).
OCHA_REVISED_PLAN_DATE = "2026-07-06"

# Contact for "report an issue / suggest a source" (site maintainer).
CONTACT_EMAIL = "amandanizagm@gmail.com"

# Contacts listed in the site footer: (label string key, display text, href).
# Edit here to add/remove footer contacts — see EDITING_GUIDE.md.
FOOTER_CONTACTS = [
    ("contact_maintainer", "amandanizagm@gmail.com", "mailto:amandanizagm@gmail.com"),
    ("contact_ofac", "ofac_feedback@treasury.gov · 1-800-540-6322",
     "mailto:ofac_feedback@treasury.gov"),
    ("contact_caf", "alianzas@caf.com · trustfunds@caf.com", "mailto:alianzas@caf.com"),
    ("contact_fts", "fts@un.org", "mailto:fts@un.org"),
]

# Currency display: symbol + rough USD rate (for aggregation labelling only;
# canonical USD amounts come straight from the seed's *_usd fields).
CURRENCY_SYMBOLS = {"USD": "$", "GBP": "£", "EUR": "€", "CHF": "CHF "}

# Canonical original-currency amounts for the few non-USD entries. Stored so
# cards can show the source figure (£7M, CHF 50M, €5M) and label the converted
# USD with "≈". Keyed by seed source id.
FUNDING_CURRENCY_OVERRIDES = {
    "dec-uk-appeal": {
        "currency": "GBP",
        "amount_committed_original": 7_000_000,   # "over £7M raised day 1"
    },
    "ifrc-emergency-appeal": {
        "currency": "CHF",
        "amount_target_original": 50_000_000,     # CHF 50M appeal
        "amount_committed_original": 2_000_000,   # CHF 2M DREF release
    },
    "eu-echo-emergency": {
        "currency": "EUR",
        "amount_committed_original": 5_000_000,   # €5M emergency release
    },
}

FUND_SOURCE_URLS = [
    {
        "name": "CAF News",
        "url": "https://www.caf.com/en/currently/news/",
        "keywords": ["venezuela", "earthquake", "reconstruction", "disaster"],
    },
    {
        "name": "IDB News",
        # /en/news was retired; the news-search app is the current listing.
        "url": "https://www.iadb.org/en/news/news-search",
        "keywords": [
            "venezuela",
            "earthquake",
            "reconstruction",
            "disaster",
            "humanitarian",
        ],
    },
    {
        "name": "U.S. State Department",
        "url": "https://www.state.gov/press-releases/",
        "keywords": ["venezuela", "earthquake"],
    },
    {
        "name": "EU Civil Protection (ECHO)",
        "url": "https://civil-protection-humanitarian-aid.ec.europa.eu/news-stories/news_en",
        "keywords": ["venezuela", "earthquake"],
    },
]

# Controlled vocabularies — must match Airtable select options (see airtable/schema.md)
AUTHORIZED_ACTIVITIES = [
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

TARGET_SECTORS = [
    "Healthcare",
    "Infrastructure",
    "WASH",
    "Housing",
    "Energy",
    "Education",
]

CAPITAL_TYPES = [
    "Grant",
    "Concessional Loan",
    "Commercial Debt",
    "Blended Finance",
]

LICENSE_STATUSES = ["Active", "Expiring Soon", "Expired", "Revoked"]
COMPLIANCE_VERDICTS = ["Green", "Yellow", "Red"]

# Funding-flow lifecycle for funds_tb.Status (Pledged → Committed → Disbursed).
# Maps from FTS flow.status: pledge→Pledged, commitment→Committed, paid→Disbursed.
FUND_STATUSES = ["Pledged", "Committed", "Disbursed"]
FTS_STATUS_MAP = {
    "pledge": "Pledged",
    "commitment": "Committed",
    "paid": "Disbursed",
}


def require_anthropic() -> str:
    """Return ANTHROPIC_API_KEY or raise if missing."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Add it to .env in the project root."
        )
    return ANTHROPIC_API_KEY


def require_airtable() -> tuple[str, str]:
    """Return (AIRTABLE_API_KEY, AIRTABLE_BASE_ID) or raise if missing."""
    if not AIRTABLE_API_KEY or not AIRTABLE_BASE_ID:
        raise RuntimeError(
            "AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in .env."
        )
    return AIRTABLE_API_KEY, AIRTABLE_BASE_ID


def airtable_configured() -> bool:
    return bool(AIRTABLE_API_KEY and AIRTABLE_BASE_ID)


def anthropic_configured() -> bool:
    return bool(ANTHROPIC_API_KEY)


def llm_configured() -> bool:
    """Blueprint uses Anthropic as the sole LLM provider."""
    return anthropic_configured()

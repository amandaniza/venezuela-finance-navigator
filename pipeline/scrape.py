"""Monitor OFAC Recent Actions and CAF/IDB fund portals for new documents.

OFAC is fetched with plain requests (no anti-bot layer). The CAF/IDB fund
portals are rendered in headless Chromium via Playwright, since both sit
behind CDN protections that 403 or break TLS for non-browser clients.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

import config

log = logging.getLogger(__name__)

ACTION_PATH_RE = re.compile(r"/recent-actions/(\d{8})", re.IGNORECASE)
MEDIA_DOWNLOAD_RE = re.compile(r"/media/\d+/download", re.IGNORECASE)
TARGET_YEAR = "2026"
SEEN_OFAC_PATH = config.STATE_DIR / "seen_ofac.json"
SEEN_FUNDS_PATH = config.STATE_DIR / "seen_funds.json"


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36 "
                f"({config.USER_AGENT})"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
        }
    )
    try:
        import certifi

        session.verify = certifi.where()
    except ImportError:
        pass
    return session



def _load_seen(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return set(data.get("seen_ids", []))
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Could not read %s (%s); starting fresh.", path, exc)
        return set()


def _save_seen(path: Path, seen: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "seen_ids": sorted(seen),
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def content_hash(*parts: str) -> str:
    raw = "|".join(p.strip() for p in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def is_pdf_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path.endswith(".pdf"):
        return True
    if MEDIA_DOWNLOAD_RE.search(path):
        return True
    return "pdf" in path


def is_recent_action_url(url: str) -> bool:
    return bool(ACTION_PATH_RE.search(urlparse(url).path))


def action_year_from_url(url: str) -> str | None:
    match = ACTION_PATH_RE.search(urlparse(url).path)
    if not match:
        return None
    return match.group(1)[:4]


def fetch_html(url: str, session: requests.Session | None = None) -> str:
    sess = session or _session()
    resp = sess.get(url, timeout=config.HTTP_TIMEOUT)
    resp.raise_for_status()
    return resp.text


def filename_from_response(url: str, resp: requests.Response) -> str:
    disposition = resp.headers.get("Content-Disposition", "")
    match = re.search(
        r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', disposition, re.IGNORECASE
    )
    if match:
        name = Path(match.group(1).strip()).name
    else:
        name = Path(urlparse(url).path).name or "document.pdf"
        if name.lower() == "download":
            name = "document.pdf"
    name = re.sub(r"[^\w.\-]+", "_", name)
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def download_pdf(url: str, session: requests.Session | None = None) -> Path | None:
    sess = session or _session()
    config.PDF_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:10]
    existing = list(config.PDF_DIR.glob(f"{digest}_*.pdf"))
    if existing and existing[0].stat().st_size > 0:
        log.info("PDF already on disk: %s", existing[0].name)
        return existing[0]

    try:
        resp = sess.get(url, timeout=120)
        resp.raise_for_status()
        body = resp.content
        content_type = resp.headers.get("Content-Type", "")
        is_pdf = (
            "pdf" in content_type.lower()
            or body[:4] == b"%PDF"
            or is_pdf_url(url)
        )
        if not is_pdf:
            log.warning("Skipping non-PDF from %s (%s)", url, content_type)
            return None
        name = filename_from_response(url, resp)
        dest = config.PDF_DIR / f"{digest}_{name}"
        dest.write_bytes(body)
        log.info("Downloaded %s (%d bytes)", dest.name, len(body))
        return dest
    except requests.RequestException as exc:
        log.error("Download failed for %s: %s", url, exc)
        return None


def extract_text_from_pdf(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            log.warning("Page %d of %s failed: %s", i, pdf_path.name, exc)
            text = ""
        pages.append(text)
    return "\n\n".join(pages).strip()


# ---------------------------------------------------------------------------
# OFAC
# ---------------------------------------------------------------------------

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
            for sibling_a in parent.find_all("a", href=True):
                sibling_url = urljoin(base_url, sibling_a["href"].strip())
                if is_pdf_url(sibling_url):
                    pdf_urls.append(sibling_url)

        entries.append(
            {
                "id": content_hash(full, title)[:16],
                "title": title,
                "url": full,
                "text": context,
                "pdf_urls": list(dict.fromkeys(pdf_urls)),
            }
        )
    return entries


def entry_mentions_venezuela(entry: dict[str, Any]) -> bool:
    keyword = config.VENEZUELA_KEYWORD.lower()
    if keyword in entry.get("title", "").lower():
        return True
    return keyword in entry.get("text", "").lower()


def entry_is_target_year(entry: dict[str, Any], year: str = TARGET_YEAR) -> bool:
    """Keep only Recent Actions issued in the target year (path date or text)."""
    url_year = action_year_from_url(entry.get("url", ""))
    if url_year == year:
        return True
    blob = f"{entry.get('title', '')} {entry.get('text', '')} {entry.get('url', '')}"
    return year in blob


def collect_pdf_urls_from_detail(
    entry_url: str, session: requests.Session
) -> list[str]:
    if is_pdf_url(entry_url):
        return [entry_url]
    try:
        html = fetch_html(entry_url, session)
    except requests.RequestException as exc:
        log.warning("Failed to open action page %s: %s", entry_url, exc)
        return []
    soup = BeautifulSoup(html, "lxml")
    pdfs = [
        urljoin(entry_url, a["href"].strip())
        for a in soup.find_all("a", href=True)
        if is_pdf_url(urljoin(entry_url, a["href"].strip()))
    ]
    return list(dict.fromkeys(pdfs))


def scrape_ofac(
    *,
    force_all: bool = False,
) -> list[dict[str, Any]]:
    """
    Return new Venezuela-related OFAC documents issued in TARGET_YEAR.

    Targets the U.S. Treasury OFAC Recent Actions page, filters for
    'Venezuela' and the issuance year, downloads PDFs, extracts text.

    Each item:
      id, title, url, pdf_url, pdf_path, text, content_hash, source_type="ofac"
    """
    session = _session()
    log.info("Fetching %s", config.OFAC_RECENT_ACTIONS_URL)
    html = fetch_html(config.OFAC_RECENT_ACTIONS_URL, session)
    entries = parse_recent_actions(html, config.OFAC_RECENT_ACTIONS_URL)
    venezuela = [
        e
        for e in entries
        if entry_mentions_venezuela(e) and entry_is_target_year(e, TARGET_YEAR)
    ]
    log.info(
        "OFAC: %d Venezuela-related entr(y/ies) in %s",
        len(venezuela),
        TARGET_YEAR,
    )

    seen = set() if force_all else _load_seen(SEEN_OFAC_PATH)
    documents: list[dict[str, Any]] = []

    for entry in venezuela:
        if entry["id"] in seen:
            continue
        pdf_urls = list(entry.get("pdf_urls") or [])
        if not pdf_urls:
            pdf_urls = collect_pdf_urls_from_detail(entry["url"], session)
        if not pdf_urls:
            log.warning("No PDFs for %s", entry["url"])
            seen.add(entry["id"])
            continue

        for pdf_url in pdf_urls:
            pdf_path = download_pdf(pdf_url, session)
            if pdf_path is None:
                continue
            text = extract_text_from_pdf(pdf_path)
            if not text:
                log.warning("No text in %s", pdf_path.name)
                continue
            documents.append(
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "url": entry["url"],
                    "pdf_url": pdf_url,
                    "pdf_path": str(pdf_path),
                    "text": text,
                    "content_hash": content_hash(pdf_url, entry["title"]),
                    "source_type": "ofac",
                }
            )
        seen.add(entry["id"])

    _save_seen(SEEN_OFAC_PATH, seen)
    return documents


# ---------------------------------------------------------------------------
# Fund portals (CAF / IDB) — headless browser
#
# CAF and IDB sit behind CDN anti-bot layers that reject plain requests
# (403 Forbidden, TLS handshake failures). We render each portal in headless
# Chromium via Playwright and parse the resulting DOM instead.
# ---------------------------------------------------------------------------

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0.0.0 Safari/537.36"
)
BROWSER_NAV_TIMEOUT_MS = 45_000
BROWSER_SETTLE_TIMEOUT_MS = 10_000
BROWSER_RENDER_GRACE_MS = 2_000

# Portals like IDB build their pages from web components; press-release
# cards live inside open shadow roots, which page.content() does not
# serialize. Clone each shadow root's HTML into its host so BeautifulSoup
# can see the full rendered DOM.
_EXPAND_SHADOW_DOM_JS = """
() => {
  const expand = (root) => {
    for (const el of root.querySelectorAll('*')) {
      if (el.shadowRoot) {
        expand(el.shadowRoot);
        const holder = document.createElement('div');
        holder.setAttribute('data-shadow-expanded', '');
        holder.innerHTML = el.shadowRoot.innerHTML;
        el.appendChild(holder);
      }
    }
  };
  expand(document);
}
"""


class BrowserUnavailableError(RuntimeError):
    """Playwright is not installed or its Chromium build is missing."""


class BrowserSession:
    """One headless Chromium context reused across all portal fetches."""

    def __init__(self) -> None:
        self._pw = None
        self._browser = None
        self._context = None

    def __enter__(self) -> "BrowserSession":
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise BrowserUnavailableError(
                "Playwright is not installed. Run: pip install playwright "
                "&& playwright install chromium"
            ) from exc

        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as exc:  # noqa: BLE001 — missing browser binary
            self._pw.stop()
            self._pw = None
            raise BrowserUnavailableError(
                "Chromium is not installed for Playwright. "
                "Run: playwright install chromium"
            ) from exc

        self._context = self._browser.new_context(
            user_agent=BROWSER_UA,
            locale="en-US",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9,es;q=0.8"},
            ignore_https_errors=True,
        )
        self._context.set_default_navigation_timeout(BROWSER_NAV_TIMEOUT_MS)
        # Basic anti-bot hygiene: headless Chromium exposes webdriver=true.
        self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', "
            "{get: () => undefined});"
        )
        return self

    def __exit__(self, *exc_info: object) -> None:
        for closer in (self._context, self._browser):
            try:
                if closer is not None:
                    closer.close()
            except Exception:  # noqa: BLE001
                pass
        if self._pw is not None:
            self._pw.stop()
        self._context = self._browser = self._pw = None

    def fetch_rendered_html(self, url: str, *, referer: str | None = None) -> str:
        """Navigate to `url` and return the rendered DOM as HTML.

        Pass the listing page as `referer` when opening detail pages —
        CDNs (e.g. IDB's) 403 deep links that arrive without one.
        """
        from playwright.sync_api import Error as PlaywrightError

        assert self._context is not None, "BrowserSession not entered"
        page = self._context.new_page()
        try:
            response = page.goto(url, wait_until="domcontentloaded", referer=referer)
            if response is not None and response.status >= 400:
                raise PlaywrightError(
                    f"HTTP {response.status} for {url}"
                )
            # Dismiss OneTrust cookie banners (IDB gates rendering on it).
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3_000)
            except PlaywrightError:
                pass
            # Let client-side listings (news grids, search apps) finish.
            try:
                page.wait_for_load_state(
                    "networkidle", timeout=BROWSER_SETTLE_TIMEOUT_MS
                )
            except PlaywrightError:
                pass  # busy pages never go idle; DOM is good enough
            page.wait_for_timeout(BROWSER_RENDER_GRACE_MS)
            try:
                page.evaluate(_EXPAND_SHADOW_DOM_JS)
            except PlaywrightError:
                pass
            return page.content()
        finally:
            page.close()


def _matches_keywords(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(k.lower() in lower for k in keywords)


def _candidates_from_html(
    html: str, source_url: str, keywords: list[str]
) -> list[tuple[str, str, str]]:
    soup = BeautifulSoup(html, "lxml")
    candidates: list[tuple[str, str, str]] = []

    # RSS / Atom
    for item in soup.find_all(["item", "entry"]):
        title_el = item.find("title")
        link_el = item.find("link")
        desc_el = item.find(["description", "summary", "content"])
        title = title_el.get_text(" ", strip=True) if title_el else ""
        href = ""
        if link_el:
            href = (link_el.get("href") or link_el.get_text(" ", strip=True) or "").strip()
        context = desc_el.get_text(" ", strip=True) if desc_el else title
        if title and href and _matches_keywords(f"{title} {context}", keywords):
            candidates.append((title, urljoin(source_url, href), context))

    # Anchors with real link text first, attribute/slug-titled ones after,
    # so URL-level dedupe downstream keeps the human-readable headline.
    source_base = urljoin(source_url, urlparse(source_url).path)
    fallback_candidates: list[tuple[str, str, str]] = []
    for a in soup.find_all("a", href=True):
        raw_href = a["href"].strip()
        if raw_href.startswith(("mailto:", "#")):
            continue
        href = urljoin(source_url, raw_href)
        # Drop in-page fragments and self-links back to the listing itself.
        if urljoin(href, urlparse(href).path) == source_base:
            continue
        has_text = bool(a.get_text(strip=True))
        title = _title_for_anchor(a, href)
        if not title or len(title) < 12:
            continue
        # Match keywords against the title, the URL slug, and the *tight*
        # local context. The slug is the most reliable signal (a Venezuela
        # story's URL contains "venezuela"); local context is only trusted
        # when teaser-sized, so a mega-nav (e.g. State's country dropdown that
        # lists "Venezuela") can't make every country link falsely match.
        slug_words = urlparse(href).path.replace("-", " ").replace("_", " ")
        tight = _local_context(a)
        match_context = tight if len(tight) <= CONTEXT_MATCH_CAP else ""
        if not _matches_keywords(f"{title} {slug_words} {match_context}", keywords):
            continue
        # Carry the richer card-level context as the body-text fallback for
        # when the detail page can't be fetched (e.g. Cloudflare-blocked).
        rich = _anchor_context(a, title)
        bucket = candidates if has_text else fallback_candidates
        bucket.append((title, href, rich or tight or title))

    return candidates + fallback_candidates


CONTEXT_MIN_CHARS = 200
# Above this, a "local" context is really a nav/grid block, not a card teaser,
# so we don't trust it for keyword matching.
CONTEXT_MATCH_CAP = 600


def _local_context(a: Any) -> str:
    """Text of the anchor's immediate list/card parent — its own teaser.

    Deliberately shallow: used for keyword matching so an anchor only
    matches on nearby text, never on unrelated stories elsewhere in the
    listing. For card layouts whose anchor sits in an empty wrapper this
    is blank, and matching falls back to the (slug-derived) title.
    """
    parent = a.find_parent(["li", "article", "div", "tr"])
    return " ".join(parent.stripped_strings) if parent else ""


def _anchor_context(a: Any, title: str) -> str:
    """Text of the nearest ancestor that actually carries a summary.

    Card layouts (e.g. IDB's <idb-news-card>) wrap the anchor in empty
    <div>s; the teaser text lives a few levels up. Walk bottom-up and take
    the first ancestor with enough text, which is the tightest card-level
    container rather than the whole listing grid.
    """
    node = a
    for _ in range(8):
        node = node.parent
        if node is None:
            break
        text = " ".join(node.stripped_strings)
        if len(text) >= CONTEXT_MIN_CHARS:
            return text[:50_000]
    parent = a.find_parent(["li", "article", "div", "tr"])
    return " ".join(parent.stripped_strings) if parent else title


def _title_for_anchor(a: Any, href: str) -> str:
    """Anchor text, falling back to attributes and finally the URL slug.

    Card-style listings (e.g. IDB web components) often wrap an image in
    an anchor with no visible text — the slug still carries the headline.
    """
    title = a.get_text(" ", strip=True)
    if title:
        return title
    for attr in ("aria-label", "title"):
        value = (a.get(attr) or "").strip()
        if value:
            return value
    img = a.find("img", alt=True)
    if img and img["alt"].strip():
        return img["alt"].strip()
    segments = [s for s in urlparse(href).path.split("/") if s]
    if segments:
        return segments[-1].replace("-", " ").replace("_", " ").strip().capitalize()
    return ""


def _load_local_fund_samples(seen: set[str]) -> list[dict[str, Any]]:
    """Process checked-in sample press releases when live portals are blocked."""
    sample_dir = config.SEED_DIR / "fund_samples"
    if not sample_dir.exists():
        return []
    documents: list[dict[str, Any]] = []
    for path in sorted(sample_dir.glob("*.txt")):
        title = path.stem.replace("_", " ").title()
        text = path.read_text(encoding="utf-8")
        url = f"file://{path.as_posix()}"
        doc_id = content_hash(url, title)[:16]
        if doc_id in seen:
            continue
        documents.append(
            {
                "id": doc_id,
                "title": title,
                "url": url,
                "pdf_url": None,
                "pdf_path": None,
                "text": text,
                "content_hash": content_hash(url, title),
                "source_type": "fund",
                "source_name": "local_sample",
            }
        )
        seen.add(doc_id)
        log.info("Fund sample: %s", path.name)
    return documents


def _extract_detail_text(detail_html: str) -> str:
    """Strip chrome from a rendered press-release page, keep article text.

    Considers every <article>/<main> plus <body> and keeps the one with the
    most text — sites like CAF use <article> for sidebar teaser cards, so
    the first match is not necessarily the story.
    """
    detail_soup = BeautifulSoup(detail_html, "lxml")
    for tag in detail_soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    texts = [
        " ".join(c.stripped_strings)
        for c in detail_soup.find_all(["article", "main"])
    ]
    best = max(texts, key=len, default="")
    if len(best) >= 500:
        return best
    body = detail_soup.body
    body_text = " ".join(body.stripped_strings) if body else ""
    return body_text if len(body_text) > len(best) else best


def _scrape_fund_source(
    browser: BrowserSession,
    source: dict[str, Any],
    seen: set[str],
) -> list[dict[str, Any]]:
    """Render one portal listing, follow matching entries, return documents."""
    from playwright.sync_api import Error as PlaywrightError

    source_url = source["url"]
    keywords = source["keywords"]
    log.info("Rendering fund portal: %s", source_url)
    try:
        html = browser.fetch_rendered_html(source_url)
    except PlaywrightError as exc:
        log.error("Fund portal render failed (%s): %s", source_url, exc)
        return []

    candidates = _candidates_from_html(html, source_url, keywords)
    log.info("%s: %d keyword-matching candidate(s)", source["name"], len(candidates))

    documents: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for title, href, context in candidates:
        if href in seen_urls:
            continue
        seen_urls.add(href)
        doc_id = content_hash(href, title)[:16]
        if doc_id in seen:
            continue

        body_text = context
        try:
            detail_text = _extract_detail_text(
                browser.fetch_rendered_html(href, referer=source_url)
            )
            if detail_text:
                body_text = detail_text
        except PlaywrightError as exc:
            log.warning("Detail render failed (%s): %s", href, exc)

        if not _matches_keywords(f"{title} {body_text}", keywords):
            continue

        snippet_path = config.HTML_DIR / f"{doc_id}.txt"
        snippet_path.write_text(body_text[:50_000], encoding="utf-8")

        documents.append(
            {
                "id": doc_id,
                "title": title,
                "url": href,
                "pdf_url": None,
                "pdf_path": None,
                "text": body_text[:50_000],
                "content_hash": content_hash(href, title),
                "source_type": "fund",
                "source_name": source["name"],
            }
        )
        seen.add(doc_id)
        log.info("Fund candidate: %s (%s)", title[:80], href)
    return documents


def scrape_fund_portals(
    *,
    force_all: bool = False,
) -> list[dict[str, Any]]:
    """
    Scrape configured fund portal listing pages for relevant press releases.

    Renders each portal in headless Chromium (Playwright) to get past the
    anti-bot protections that block plain requests, then parses the DOM for
    entries matching the source keywords (Venezuela, earthquake, ...).

    Returns documents with rendered body text for LLM extraction into
    funds_tb. Falls back to data/seed/fund_samples when live portals yield
    nothing (e.g. Playwright missing or every portal blocked).
    """
    seen = set() if force_all else _load_seen(SEEN_FUNDS_PATH)
    documents: list[dict[str, Any]] = []
    config.HTML_DIR.mkdir(parents=True, exist_ok=True)

    try:
        with BrowserSession() as browser:
            for source in config.FUND_SOURCE_URLS:
                documents.extend(_scrape_fund_source(browser, source, seen))
    except BrowserUnavailableError as exc:
        log.error("%s", exc)

    if not documents:
        log.warning(
            "No live fund-portal documents; loading local samples from %s",
            config.SEED_DIR / "fund_samples",
        )
        documents.extend(_load_local_fund_samples(seen))

    _save_seen(SEEN_FUNDS_PATH, seen)
    return documents




def scrape_all(*, force_all: bool = False) -> dict[str, list[dict[str, Any]]]:
    return {
        "ofac": scrape_ofac(force_all=force_all),
        "funds": scrape_fund_portals(force_all=force_all),
    }

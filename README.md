# Venezuela Reconstruction Finance Navigator (Phase 1 MVP)

Bilingual intelligence dashboard that maps earthquake relief and reconstruction
capital to active U.S. OFAC General Licenses, enabling rapid, compliant
deployment of funds in Venezuela.

> **Maintaining the site?** See [EDITING_GUIDE.md](EDITING_GUIDE.md) — how to
> add/edit funding sources, footer contacts, and site text, and how to publish
> changes. Questions: amandanizagm@gmail.com

**Personas**

- **Capital Provider (D.C.)** — verify whether a funding tranche falls under an
  active GL (e.g. GL 60) or needs a specific application (e.g. GL 56).
- **Relief Operator (Caracas / La Guaira)** — Spanish-first filters for funding
  pools by eligible sector and capital type.

## Stack

| Layer | Tooling |
| --- | --- |
| Ingestion | Python, BeautifulSoup, PyPDF2 |
| NLP | OpenAI / Anthropic (JSON-schema extraction) |
| Database | Airtable (or local JSON fallback) |
| Frontend | Streamlit |

## Quick start

```powershell
cd C:\Users\amimi\venezuela-finance-navigator
C:\Users\amimi\anaconda3\python.exe -m pip install -r requirements.txt
copy .env.example .env
# Optional: set OPENAI_API_KEY / AIRTABLE_* in .env

# Load demo pathways (GL 60, GL 56, sample funds)
C:\Users\amimi\anaconda3\python.exe scripts\seed_demo.py --reset

# Launch dashboard (defaults to Spanish)
C:\Users\amimi\anaconda3\python.exe -m streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

## Airtable setup

See [airtable/schema.md](airtable/schema.md) for the exact field checklist.

1. Create tables `licenses_tb`, `funds_tb`, `pathways_tb`.
2. Create a Personal Access Token with `data.records:read` and `data.records:write`.
3. Put `AIRTABLE_API_KEY` and `AIRTABLE_BASE_ID` in `.env`.
4. Re-run `python scripts/seed_demo.py`.

Without Airtable credentials the app uses `data/seed/local_db.json`.

## Daily pipeline

```powershell
# Full run: OFAC + fund portals → LLM → Airtable/local upsert
C:\Users\amimi\anaconda3\python.exe pipeline\run_daily.py

# Scrape only (no LLM / no writes)
C:\Users\amimi\anaconda3\python.exe pipeline\run_daily.py --dry-run

# Re-process everything
C:\Users\amimi\anaconda3\python.exe pipeline\run_daily.py --force-all

# OFAC licenses only / fund portals only
C:\Users\amimi\anaconda3\python.exe pipeline\run_daily.py --ofac-only
C:\Users\amimi\anaconda3\python.exe pipeline\run_daily.py --funds-only
```

Machine-loaded rows always have `Human_Verified = false`. A compliance officer
links funds to licenses in Airtable (`pathways_tb`) and checks
`Human_Verified` before pathways appear in Streamlit.

### Windows Task Scheduler

1. Create a Basic Task → Daily → Start a program.
2. Program: `C:\Users\amimi\anaconda3\python.exe`
3. Arguments: `pipeline\run_daily.py`
4. Start in: `C:\Users\amimi\venezuela-finance-navigator`

### cron (Linux / macOS)

```bash
0 6 * * * cd /path/to/venezuela-finance-navigator && python pipeline/run_daily.py >> data/pipeline.log 2>&1
```

## Repository layout

```
app.py                  # Streamlit dashboard
config.py               # env, vocabularies, paths
i18n/strings.py         # EN / ES UI copy
airtable/               # client + schema checklist
pipeline/
  scrape.py             # OFAC + CAF/IDB monitors
  extract.py            # LLM → licenses_tb / funds_tb JSON
  load_airtable.py      # upsert (Human_Verified=False)
  run_daily.py          # orchestrator
scripts/seed_demo.py    # demo data loader
data/seed/              # seed JSON + local_db.json
```

## Deploying publicly (Streamlit Community Cloud)

1. Push this repo to GitHub (public).
2. At https://share.streamlit.io → **New app** → pick the repo, branch `main`,
   main file `app.py`.
3. Done — the app self-seeds on first boot (directory from
   `navigator_funding_seed.json`, licenses/pathways demo seed, live flows from
   the public UNOCHA FTS API). No secrets are required for the public site;
   API keys in `.env` are only needed for the ingestion pipeline.

Every `git push` to `main` redeploys automatically.

## Compliance notice

This tool is an operational aid for mapping public funding announcements to
public OFAC license text. It is **not legal advice**. Only human-verified
pathways are shown in the Navigator.

# Editing Guide — Reconstruction Finance Navigator

This guide shows you how to change what the site displays — funding sources,
contacts, text — whenever you want, without touching the app's plumbing.

---

## The one idea to understand

Almost everything you'll ever want to edit lives in **two files**:

| What you want to change | File to edit |
|---|---|
| Funding directory entries (add / edit / remove a fund) | `navigator_funding_seed.json` |
| Footer contacts + your maintainer email | `config.py` |
| Site text (headings, labels, both languages) | `layout.py` (the `STRINGS` block at the top) |

After editing the funding directory you run **one command** to load your
changes into the site's database (step-by-step below). Contacts and text
changes appear as soon as you restart/refresh the app.

---

## 1. Add a new funding source

1. Open `navigator_funding_seed.json` in any text editor (Notepad works).
2. Find the `"funding_sources": [` list. Copy an existing entry — everything
   from one `{` to its matching `},` — and paste it where you want the new one.
   Tip: entries with `"org_type": "community_fund"` (e.g. `cuatro-por-venezuela`)
   are good templates for community funds.
3. Edit the fields:

   | Field | What it means |
   |---|---|
   | `id` | Unique slug, lowercase-with-dashes (e.g. `my-new-fund`). Never reuse one. |
   | `name_en` / `name_es` | Display name in English / Spanish |
   | `org` | Organization behind the fund |
   | `org_type` | Controls the "Your layer" filter. Use `community_fund` for community/individually organized funds. Other common values: `ingo`, `diaspora_ngo`, `un_agency`, `grantmaker`, `crowdfunding_platform` |
   | `category` | Free-text grouping, e.g. `community_organized_fund` |
   | `flow_direction` | `accepts_contributions` (people give here), `grants_to_ngos` (NGOs apply), `both`, `direct_to_beneficiaries` |
   | `amount_target_usd` / `amount_committed_usd` | Numbers, or `null` if unknown |
   | `accepts_from` | List: `"individuals"`, `"companies"`, `"foundations"`, `"governments"` |
   | `compliance_notes` | Accreditation facts (501(c)(3), EIN, charity ratings, registration numbers) |
   | `suggested_license_pathway` | Start with `REVIEW —` unless a human has verified it |
   | `verification_status` | Keep `unverified` for new entries (`platform_vetted` only if a vetting platform like GlobalGiving hosts it) |
   | `url` | The fund's official public page — always link the authoritative source |
   | `phase` | List from: `"relief"`, `"rehabilitation"`, `"reconstruction"` |
   | `notes_es` | Spanish description shown on the detail page |

4. Save the file, then load it into the database:

   ```
   C:\Users\amimi\anaconda3\python.exe scripts\import_funding_seed.py
   ```

5. Refresh the site. The new card appears in the Directory (count updates
   automatically).

**Editing or removing** an entry works the same way: change or delete its block
in the JSON, then re-run the import command. (Removing from the JSON does not
delete the database row — to fully remove an entry, also run:
`C:\Users\amimi\anaconda3\python.exe -c "import sqlite3; c=sqlite3.connect('data/navigator.db'); c.execute('DELETE FROM funding_sources WHERE source_key=?', ('THE-ID',)); c.commit()"`
replacing `THE-ID` with the entry's `id`.)

**JSON gotchas:** every entry except the last needs a trailing comma; text goes
in double quotes; `null` (not empty) for unknown numbers. If the site errors
after an edit, it's almost always a missing/extra comma — paste the file into
https://jsonlint.com to find the exact spot.

---

## 2. Edit the footer contacts

Open `config.py` and find `FOOTER_CONTACTS`. Each line is one footer card:

```python
FOOTER_CONTACTS = [
    ("contact_maintainer", "amandanizagm@gmail.com", "mailto:amandanizagm@gmail.com"),
    ...
]
```

- The first item is the label key — its display text (EN + ES) lives in the
  `STRINGS` block in `layout.py` (search for `contact_maintainer`).
- The second is what's shown; the third is the link (use `mailto:` for email,
  `https://` for pages).
- Add or delete lines to add or remove contacts. To add a brand-new label,
  add a new key to BOTH the `"en"` and `"es"` sections of `STRINGS`.

`CONTACT_EMAIL` (also in `config.py`) is where "Report an issue" and the
signup form point — it's set to your email.

---

## 3. Edit site text (both languages)

All copy lives in `layout.py`, in the `STRINGS` dictionary near the top —
one `"en"` section and one `"es"` section with matching keys. Change the text
in quotes; keep placeholders like `{count}` or `{date}` intact.

**Copy standard (applies to all new text):**

- Understandable with no finance or legal background. If a sentence needs a
  law degree to parse, rewrite it. Legal-register phrasing belongs only in
  the linked official license text, never in site copy.
- Say what it means for the reader first, detail after.
- Spell out every acronym on its first use **on each page** (OFAC, GL, OCHA,
  FTS, NGO/ONG, MDB, INGO...). A visitor landing on an inner page from a
  search must not hit an unexplained acronym.
- Each language reads as if written natively in it. No English words inside
  Spanish sentences or vice versa (proper names excepted).
- Spanish is gender-neutral, formal (usted). Short declarative sentences,
  no em dashes, in both languages.

---

## 3b. The intent paths (Donate / Send money)

The two intent cards on Home route as follows:

- **"I want to donate"** lands on the Directory pre-filtered to giving flows
  (`/directory?fd=give`). There is no separate donate page; entries appear in
  that view when their `flow_direction` is a giving flow. Edit entries in the
  directory data as usual.
- **"I want to send money"** lands on `/send-money`, which is not
  directory-driven: its copy lives in `STRINGS` (`rem_*` keys) and it
  deep-links to the GL 57 card on the Licenses page.
  ⚠️ The GL 57 entry in `scripts/seed_demo.py` was drafted from a summary —
  verify it against the official license text before treating it as final.

---

## 3c. The NGO funding-seeking path (tiers)

The Home banner **"¿Busca financiamiento para su organización?"** lands on
the Directory's applicant view (`/directory?fd=seek`), which groups entries
into three tiers via the `applicant_tier` field in
`navigator_funding_seed.json`:

| Tier value | Label on site | Meaning |
|---|---|---|
| `open` | Solicitud abierta | Structured application an org can start today. Also set `"accepts_applications": true`. |
| `partnership` | Vía alianza | Funds local orgs via relationship/invitation, not an open call. |
| `enabler` | Habilitadores | Not a funder; unlocks or speeds up money from elsewhere. |

**Never present a partnership/enabler entry as an open grant call** — that
erodes trust with exactly the users this tab serves. Each applicant-facing
entry also carries `how_to_apply` (EN) and `how_to_apply_es` (the "Cómo
postular" box on its detail page). Leave `applicant_tier` out entirely for
donor-facing-only entries. After editing, re-run the import command from
section 1.

**Deliberately excluded from this tab** (so the question doesn't recur):
IFRC/DREF (flows only through the Venezuelan Red Cross), EU/ECHO
(pre-certified framework partners only), the US State Dept $150M pledge (no
open application channel as of 2026-07-11 — worth rechecking grants.gov and
state.gov for Venezuela NOFOs; if one appears it becomes an `open` entry),
and PayPal Grant Payments (**held**: whether Venezuela-domiciled orgs can
use it is unresolved — resolve or drop before adding). Full notes in the
seed's `meta.applicant_pass`.

---

## 4. Licenses, pathways, and live funding flows

- **Licenses & flows** are ingested by the pipeline (`python run_pipeline.py`)
  from OFAC and UNOCHA FTS — you don't edit those by hand.
- **Compliance verdicts** (Green/Yellow/Red) are set on the hidden Admin page:
  open any page and add `?auth=admin` to the URL.

---

## 5. Run the site on your computer

```
C:\Users\amimi\anaconda3\python.exe -m streamlit run app.py
```

Plain `python` may not work on this machine — use the full path above.

---

## 6. Publish your changes to the public site

Once the site is on GitHub + Streamlit Community Cloud, publishing an edit is:

```
git add -A
git commit -m "Describe what you changed"
git push
```

Streamlit Community Cloud redeploys automatically within a minute or two of
each push. Note: the public site rebuilds its database from
`navigator_funding_seed.json` on deploy, so directory edits only need the JSON
change committed — the import runs automatically there (and `data/navigator.db`
itself is never committed).

**Never commit `.env`** — it holds API keys and is already ignored by git.

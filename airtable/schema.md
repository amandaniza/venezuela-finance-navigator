# Airtable schema — Venezuela Reconstruction Finance Navigator

Field names are **case-sensitive** and must match exactly so `airtable/client.py`,
`scraper.py`, and the Streamlit app can read/write without mapping layers.

Create one base with three tables.

---

## Table 1: `licenses_tb` (OFAC Licenses)

| Field | Type | Options / notes |
| --- | --- | --- |
| `License_ID` | Single line text | Primary display field. e.g. `GL 60`, `GL 46C` |
| `Status` | Single select | `Active`, `Expiring Soon`, `Expired`, `Revoked` |
| `Expiration_Date` | Date | Pipeline uses `YYYY-MM-DD` |
| `Authorized_Activities` | Multiple select | See options below |
| `Excluded_Entities` | Long text | Explicitly banned actors (e.g. PdVSA, Minerven) |
| `Source_URL` | URL | Origin OFAC document / press release |
| `Content_Hash` | Single line text | Dedupe key (`sha256` of source URL + title) |
| `Raw_Snippet` | Long text | Short excerpt for human review |
| `Human_Verified` | Checkbox | Machine loads **always** set `false` |

### `Authorized_Activities` options

`Rubble Removal`, `Hospital Repair`, `Hospital Stabilization`, `Oil Extraction`,
`Water Sanitation`, `WASH`, `Housing Repair`, `Infrastructure Repair`,
`Humanitarian Aid`, `Energy Restoration`

### Scraper field aliases

`scraper.py` may emit human-readable keys. The client normalizes them:

| Scraper / LLM key | Airtable field |
| --- | --- |
| `License Number` | `License_ID` |
| `Expiration Date` | `Expiration_Date` |
| `Authorized Activities` | `Authorized_Activities` |
| `Exclusions` | `Excluded_Entities` |
| `Status` | `Status` |

---

## Table 2: `funds_tb` (Funding Sources)

| Field | Type | Options / notes |
| --- | --- | --- |
| `Fund_Name` | Single line text | Primary display field |
| `Capital_Type` | Single select | `Grant`, `Concessional Loan`, `Commercial Debt`, `Blended Finance` |
| `Target_Sectors` | Multiple select | `Healthcare`, `Infrastructure`, `WASH`, `Housing`, `Energy`, `Education` |
| `Source_URL` | URL | Press release or portal page |
| `Content_Hash` | Single line text | Dedupe key |
| `Raw_Snippet` | Long text | |
| `Human_Verified` | Checkbox | Machine loads **always** set `false` |

---

## Table 3: `pathways_tb` (The Map)

Core product value: many-to-many bridge between money and regulations.

| Field | Type | Options / notes |
| --- | --- | --- |
| `Map_ID` | Number (integer) | Primary display field. Autonumber is not creatable via API; convert in the UI if preferred. |
| `Linked_Fund` | Link to `funds_tb` | Allow linking to **one** record |
| `Governing_License` | Link to `licenses_tb` | Allow linking to **one** record |
| `Compliance_Verdict` | Single select | `Green`, `Yellow`, `Red` |
| `Human_Verified` | Checkbox | **Must be `true`** for Streamlit to display the row |

### Verdict meanings

| Verdict | Meaning |
| --- | --- |
| **Green** | Pre-authorized under the linked license |
| **Yellow** | Requires specific caveats / additional diligence |
| **Red** | Prohibited under the linked license |

Pathways are **not** auto-created by the pipeline. A compliance officer links
fund ↔ license and sets the verdict in Airtable.

---

## Setup checklist

1. Create a new Airtable base.
2. Create tables `licenses_tb`, `funds_tb`, and `pathways_tb` with the fields above.
3. Create a Personal Access Token with `data.records:read` and `data.records:write`.
4. Copy the base ID (`appXXXXXXXXXXXXXX`) from the API docs URL.
5. Put credentials in `.env`:

```
ANTHROPIC_API_KEY=...
AIRTABLE_API_KEY=...
AIRTABLE_BASE_ID=appXXXXXXXXXXXXXX
AIRTABLE_TABLE_LICENSES=licenses_tb
AIRTABLE_TABLE_FUNDS=funds_tb
AIRTABLE_TABLE_PATHWAYS=pathways_tb
```

6. Confirm connectivity:

```powershell
python -c "from airtable.client import AirtableClient; print(AirtableClient().ping())"
```

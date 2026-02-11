# Veteran Organization Directory — Project Guide

## What This Is

A comprehensive directory of **80,784 US veteran/military support organizations**, built for the nonprofit **Active Heroes** (Shepherdsville, KY) to identify partners, funders, and peer organizations. The project has two parts:

1. **Data pipeline** (`main.py`) — ETL that collects, enriches, deduplicates, and outputs a single CSV
2. **Streamlit dashboard** (`app.py`) — Interactive web app for searching/filtering the directory

Live app: Deployed on Streamlit Community Cloud via GitHub repo `vinceRM17/vet-org-directory`.

---

## Project Structure

```
config/
  settings.py          # URLs, paths, rate limits, API key refs
  ntee_codes.py        # NTEE filters + veteran keyword list (119 keywords)
  schema.py            # 50-column DataFrame schema + confidence weights
extractors/
  base_extractor.py    # Abstract base class
  irs_bmf.py           # IRS Exempt Orgs BMF bulk CSV (PRIMARY — 80K+ orgs)
  propublica.py        # ProPublica API enrichment (financials per EIN)
  va_vso.py            # VA VSO accreditation directory (Excel dumps)
  charity_nav.py       # Charity Navigator GraphQL (needs API key — not configured)
  va_facilities.py     # VA Lighthouse Facilities API (needs API key — not configured)
  nrd.py               # National Resource Directory (JSON API + sitemap)
  nodc.py              # Nonprofit Open Data Collective (not working — URLs changed)
transformers/
  normalizer.py        # EIN, phone, URL, address standardization
  enricher.py          # Web scrape org websites for social/email (Stage 7)
loaders/
  deduplicator.py      # 3-tier: exact EIN → fuzzy name+city → URL domain
  merger.py            # Multi-source merge with priority rules
  csv_writer.py        # Final CSV + confidence scores + summary report
utils/
  http_client.py       # Rate-limited requests with retry + disk cache
  checkpoint.py        # Pickle-based save/resume
main.py                # 8-stage pipeline orchestrator (--resume, --clean, --skip-enrichment, --stages)
app.py                 # Streamlit dashboard (6 tabs)
analyze_for_active_heroes.py  # Active Heroes strategic analysis (6 filtered views)
data/
  raw/                 # Downloaded source files (gitignored)
  intermediate/        # Per-source parquet (gitignored)
  output/
    veteran_org_directory.csv   # THE OUTPUT — 80,784 orgs
    summary_report.txt
    active_heroes/              # 6 filtered CSVs + dashboard
```

---

## Pipeline Stages

Run: `python3 main.py [flags]`

| Stage | What | Time | Status |
|-------|------|------|--------|
| 1 | IRS BMF download + 3-tier filter (NTEE W, 501(c)(19), keywords) | ~15 min | Working |
| 2 | ProPublica API enrichment (financials per EIN) | ~5-8 hrs | Working (checkpoints every 500) |
| 3 | VA VSO + NRD web scraping | ~1 hr | Working |
| 4 | VA Facilities API + NODC | ~30 min | Needs API keys / NODC broken |
| 5 | Merge all sources | ~5 min | Working |
| 6 | Deduplication (3-tier) | ~15 min | Working |
| 7 | Web enrichment (scrape websites for email/social) | ~10-20 hrs | Skipped so far |
| 8 | CSV output + summary report | ~2 min | Working |

Useful flags:
- `--resume` — pick up from last checkpoint
- `--skip-enrichment` — skip Stage 7
- `--stages 1,5,6,8` — run only specific stages
- `--clean` — start fresh

---

## Known Gaps

- **Contact info is sparse**: 83 phones, 0 emails, 1 website (IRS BMF doesn't have these; Stage 7 web enrichment would fill them)
- **Charity Navigator**: Needs free API key in `.env` as `CHARITY_NAV_API_KEY`
- **VA Facilities**: Needs free API key in `.env` as `VA_FACILITIES_API_KEY`
- **NODC extractor**: GitHub CSV URLs have changed; needs URL updates
- **Social media**: All empty without Stage 7 enrichment

---

## Dependencies

- **Pipeline**: `pip3 install -r requirements-pipeline.txt` (pandas, pyarrow, requests, aiohttp, beautifulsoup4, lxml, playwright, rapidfuzz, usaddress, tqdm, python-dotenv)
- **App only**: `pip3 install -r requirements.txt` (streamlit, pandas, plotly)

Requires Python 3.9+. Uses `from __future__ import annotations` for type hint compatibility.

---

## Key Decisions & Gotchas

- **Active Heroes** (EIN 45-4138378) is classified under NTEE P20 (Human Services), not a veteran code. It's captured by keyword matching on "active heroes" in `ntee_codes.py`.
- `DataFrame or default` pattern breaks in Python — always use `x = load(); var = x if x is not None else pd.DataFrame()`.
- Streamlit Cloud reads `packages.txt` as apt packages — don't use it for Python deps.
- Plotly charts must use DataFrame input (not `.index`/`.values`) for Python 3.13 compatibility.
- The `@st.cache_data(ttl=300)` on `load_data()` ensures fresh CSV is picked up within 5 minutes of deploy.

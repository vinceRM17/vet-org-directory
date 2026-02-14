# Veteran Organization Directory

A comprehensive directory of **85,000+ US veteran and military support organizations**, built for the nonprofit **Active Heroes** (Shepherdsville, KY) to identify partners, funders, and peer organizations. Includes an 8-stage ETL data pipeline and an interactive Streamlit dashboard.

## Features

- **8-Stage Data Pipeline** — Collects, enriches, deduplicates, and scores organizations from multiple federal data sources
- **Interactive Dashboard** — Search, filter, and explore organizations with maps, charts, and detail views
- **Multi-Source Aggregation** — IRS BMF, ProPublica financials, VA VSO accreditation, National Resource Directory
- **3-Tier Deduplication** — Exact EIN matching, fuzzy name+city matching, URL domain matching
- **Confidence Grading** — A through F grades based on data completeness and source verification
- **Active Heroes Analysis** — Filtered views specifically for Active Heroes' strategic planning

## Data Sources

| Source | Data | Status |
|--------|------|--------|
| IRS BMF | 85K+ orgs (primary) | Working |
| ProPublica API | Financial data per EIN | Working |
| VA VSO Directory | Accreditation data | Working |
| National Resource Directory | Federal resource listings | Working |
| Charity Navigator | Ratings & governance | Needs API key |
| VA Facilities API | VA facility locations | Needs API key |

## Project Structure

```
config/
  settings.py              # URLs, paths, rate limits
  ntee_codes.py            # NTEE filters + 119 veteran keywords
  schema.py                # 50-column schema + confidence weights
extractors/                # 8 data source extractors
transformers/
  normalizer.py            # EIN, phone, URL, address standardization
  enricher.py              # Web scrape for contact info (Stage 7)
loaders/
  deduplicator.py          # 3-tier deduplication
  merger.py                # Multi-source merge
  csv_writer.py            # Final CSV + summary report
utils/
  http_client.py           # Rate-limited requests with retry + cache
  checkpoint.py            # Save/resume pipeline state
main.py                    # Pipeline orchestrator
app.py                     # Streamlit dashboard
analyze_for_active_heroes.py  # Strategic analysis script
data/
  output/
    veteran_org_directory.csv  # The output (85K+ orgs)
    summary_report.txt
    active_heroes/             # 6 filtered CSVs
```

## Getting Started

### Dashboard only

```bash
pip install -r requirements.txt
streamlit run app.py
```

### Full pipeline

```bash
pip install -r requirements-pipeline.txt

# Copy environment variables
cp .env.example .env
# Optionally add: CHARITY_NAV_API_KEY, VA_FACILITIES_API_KEY

# Run full pipeline (~7-9 hours with ProPublica enrichment)
python main.py

# Or run specific stages
python main.py --stages 1,5,6,8

# Resume from checkpoint
python main.py --resume
```

### Pipeline Flags

| Flag | Description |
|------|-------------|
| `--resume` | Resume from last checkpoint |
| `--skip-enrichment` | Skip Stage 7 (web scraping) |
| `--stages 1,5,6,8` | Run only specific stages |
| `--clean` | Start fresh, clear checkpoints |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.9+ |
| Dashboard | Streamlit |
| Data | Pandas, PyArrow |
| Visualization | Plotly |
| Web Scraping | Requests, aiohttp, BeautifulSoup4, Playwright |
| Deduplication | RapidFuzz |
| Address Parsing | usaddress |
| Hosting | Streamlit Community Cloud |

## Environment Variables

See `.env.example`:

- `CHARITY_NAV_API_KEY` — Charity Navigator API key (free, optional)
- `VA_FACILITIES_API_KEY` — VA Facilities API key (free, optional)
- `LOG_LEVEL` — Logging verbosity (default: INFO)

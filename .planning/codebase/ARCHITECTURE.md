# Architecture

**Analysis Date:** 2026-02-11

## Pattern Overview

**Overall:** Multi-stage ETL pipeline with modular extractor-transformer-loader pattern, designed for horizontal scalability through independent data source extraction and checkpoint-based resumability.

**Key Characteristics:**
- **Extract → Transform → Checkpoint** pattern in each stage (see `BaseExtractor` in `extractors/base_extractor.py`)
- **8-stage orchestrated pipeline** with independence between stages for fault tolerance and resumability
- **Multi-source merge** with priority-based field selection (lower priority index = higher priority in conflicts)
- **3-tier deduplication** (EIN exact → fuzzy name+city → URL domain) for data quality
- **Streamlit dashboard** consumer of final CSV with real-time filtering and visualization

## Layers

**Data Extraction Layer:**
- Purpose: Download and ingest data from 7 external sources
- Location: `extractors/` directory
- Contains: Source-specific classes inheriting from `BaseExtractor` (`irs_bmf.py`, `propublica.py`, `charity_nav.py`, `va_facilities.py`, `va_vso.py`, `nrd.py`, `nodc.py`)
- Depends on: `config/settings.py` (API URLs, rate limits), `utils/http_client.py` (HTTP with retries/caching), `utils/checkpoint.py`
- Used by: `main.py` stages 1–4

**Transformation Layer:**
- Purpose: Standardize and enrich raw data
- Location: `transformers/` directory
- Contains: `normalizer.py` (EIN, phone, URL, address, state standardization), `enricher.py` (web scraping for social/email)
- Depends on: Pandas, external libraries (usaddress, regex)
- Used by: `BaseExtractor.run()` and `main.py` stages 7–8

**Loading/Merging Layer:**
- Purpose: Deduplicate, merge multi-source data, and output final CSV
- Location: `loaders/` directory
- Contains: `merger.py` (7-source priority merge on EIN + append), `deduplicator.py` (3-tier dedup), `csv_writer.py` (CSV + confidence scores + summary report)
- Depends on: `config/schema.py` (45-column canonical schema), Pandas
- Used by: `main.py` stages 5–8

**Configuration & Schema Layer:**
- Purpose: Define canonical schema, API endpoints, rate limits, file paths
- Location: `config/` directory
- Contains: `schema.py` (45-column schema with confidence weights), `settings.py` (URLs, paths, API keys), `ntee_codes.py` (NTEE veteran filters + 119 veteran keywords)
- Depends on: `python-dotenv` for environment variables
- Used by: All other layers

**Utilities Layer:**
- Purpose: HTTP requests, checkpointing, retry logic
- Location: `utils/` directory
- Contains: `http_client.py` (RateLimitedSession with disk cache), `checkpoint.py` (pickle-based save/resume)
- Depends on: Requests, urllib3, Pathlib
- Used by: All extractors and pipeline orchestrator

**Presentation Layer:**
- Purpose: Interactive search and visualization of directory
- Location: `app.py` (Streamlit dashboard)
- Contains: Sidebar filters, 6 tabs (Overview, Explore, Map, Potential Funders, Peer Network, Gap Analysis), real-time Plotly charts
- Depends on: `data/output/veteran_org_directory.csv`, Streamlit, Plotly
- Used by: Web users via Streamlit Community Cloud

## Data Flow

**Pipeline Execution (main.py):**

1. **Stage 1 (IRS BMF):** `IrsBmfExtractor.run()` downloads IRS 501(c) org data, filters by NTEE codes and veteran keywords → saved to `data/intermediate/irs_bmf.parquet`
2. **Stage 2 (API Enrichment):** `PropublicaExtractor` and `CharityNavExtractor` fetch financials for each EIN → separate parquets
3. **Stage 3 (Web Scraping):** `VaVsoExtractor` and `NrdExtractor` scrape VSO accreditation and National Resource Directory → separate parquets
4. **Stage 4 (Additional Sources):** `VaFacilitiesExtractor` and `NodcExtractor` query VA Facilities API and nonprofit open data → separate parquets
5. **Stage 5 (Merge):** `merge_all()` combines all sources with priority rules: base IRS BMF on left, EIN-based sources left-joined, non-EIN sources appended
6. **Stage 6 (Dedup):** `deduplicate()` removes duplicates in 3 tiers: exact EIN match, fuzzy name+city within state/city groups, URL domain
7. **Stage 7 (Enrichment):** `WebEnricher.enrich()` scrapes org websites for social media URLs and contact info (skippable)
8. **Stage 8 (Output):** `normalize_dataframe()` standardizes formats, `write_csv()` calculates confidence scores, outputs final CSV and summary report

**State Management:**
- **Checkpoints:** Each stage saves intermediate DataFrame to pickle in `data/checkpoints/`. Allows `--resume` flag to skip completed stages.
- **DataFrame State:** Single DataFrame passed between stages; all transformations are in-place mutations.
- **Column Tracking:** `data_sources` column appended with source name (semicolon-separated); `data_freshness_date` tracks collection date.

## Key Abstractions

**BaseExtractor (Abstract):**
- Purpose: Define common extract→transform→save pattern for all sources
- Examples: `extractors/irs_bmf.py`, `extractors/propublica.py`
- Pattern: Subclass implements `extract()` → base class handles `transform()` (override if needed) → `run()` orchestrates full pipeline with checkpoint save

**RateLimitedSession (HTTP):**
- Purpose: Centralize rate-limiting, retry logic, and disk caching for external API calls
- Examples: Used in all API extractors
- Pattern: Per-source rate limit (e.g., 2 req/sec for ProPublica) enforced via `_wait_for_rate_limit()`, retries on 429/50x via urllib3.Retry, disk cache by hash of (method, URL, params)

**Schema Coercion:**
- Purpose: Enforce 45-column canonical schema across all DataFrames
- Examples: Called in `BaseExtractor.run()`, `merger.py`, `csv_writer.py`
- Pattern: `coerce_schema(df)` fills missing columns with NaN, casts types, reorders columns to canonical order

**Priority-Based Merge:**
- Purpose: Resolve field conflicts when same org appears in multiple sources
- Examples: ProPublica has financials, Charity Navigator has ratings — merge keeps first non-null per priority list
- Pattern: `SOURCE_PRIORITY = ["irs_bmf", "propublica", "charity_nav", ...]`; lower index = higher priority

## Entry Points

**Pipeline Orchestrator:**
- Location: `main.py`
- Triggers: `python main.py [--resume] [--clean] [--skip-enrichment] [--stages 1,2,5]`
- Responsibilities: Parse CLI args, setup logging, call each stage function in sequence, handle data passing between stages, checkpoint resume logic

**Streamlit Dashboard:**
- Location: `app.py`
- Triggers: `streamlit run app.py`
- Responsibilities: Load CSV (with @st.cache_data TTL=300s), apply sidebar filters (state, org type, revenue, VA accredited, NTEE code, confidence), render 6 tabs with Plotly charts and interactive table

**Analysis Export:**
- Location: `analyze_for_active_heroes.py`
- Triggers: `python analyze_for_active_heroes.py`
- Responsibilities: Generate 6 filtered CSV exports for Active Heroes stakeholder (Active Heroes itself, VFW, Disabled American Veterans, etc.)

## Error Handling

**Strategy:** Try-except in stage functions with logging; missing API keys result in empty DataFrames that are safely handled by merger.

**Patterns:**
- **Missing API Key:** `CHARITY_NAV_API_KEY` or `VA_FACILITIES_API_KEY` not in `.env` → extractor logs warning, returns empty DataFrame → merger skips empty source
- **Network Failure:** Requests timeout/429 → urllib3.Retry retries up to `DEFAULT_RETRIES` (3) with exponential backoff → if all retries fail, requests.HTTPError raised, caught in extractor and logged
- **Invalid Data:** `pd.to_numeric(errors='coerce')` used in schema coercion to convert bad numeric strings to NaN
- **Duplicate Handling:** Deduplicator merges rows by calling `_merge_rows()` which fills NaN fields from first non-null in group; `data_sources` merged and deduplicated as set
- **Stage Skip:** If stage is skipped (e.g., `--skip-enrichment`), code loads checkpoint if available; if not, exits with error message

## Cross-Cutting Concerns

**Logging:** All modules use `logging.getLogger(__name__)`. Pipeline orchestrator in `main.py` configures root logger with dual handlers (stdout + file log to `data/output/pipeline.log`). Each extractor logs via `logging.getLogger(f"extractor.{name}")` to namespace logs.

**Validation:**
- Schema coercion enforces column names and dtypes
- Normalizers validate EIN format (9 digits), phone format (10 digits), state codes (2 letters), URLs (valid domain)
- Confidence score calculated as weighted sum of filled fields (weights in `config/schema.py`) → 0.0–1.0 range

**Authentication:** API keys loaded from environment variables via `config/settings.py` (using `python-dotenv`). Charity Navigator and VA Facilities APIs require keys; if not set, extractor returns empty DataFrame.

**Rate Limiting:** Each source has independent rate limit (e.g., ProPublica 2 req/sec, NRD 0.5 req/sec). Enforced per-session at HTTP client level via `_wait_for_rate_limit()`.

**Checkpointing:** After each extractor completes, DataFrame pickled to `data/checkpoints/extractor_{name}.pkl` and parquet saved to `data/intermediate/{name}.parquet`. Pipeline can resume from any checkpoint with `--resume` flag, skipping already-completed stages.

---

*Architecture analysis: 2026-02-11*

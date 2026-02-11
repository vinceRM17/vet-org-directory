# Codebase Structure

**Analysis Date:** 2026-02-11

## Directory Layout

```
vet_org_directory/
├── config/                      # Configuration, schema, constants
│   ├── __init__.py
│   ├── settings.py              # API URLs, paths, rate limits, API key refs
│   ├── schema.py                # 45-column canonical schema + confidence weights
│   └── ntee_codes.py            # NTEE veteran filters + 119 veteran keywords
│
├── extractors/                  # Data source extraction (7 sources)
│   ├── __init__.py
│   ├── base_extractor.py        # Abstract base class: extract → transform → checkpoint
│   ├── irs_bmf.py               # IRS Exempt Orgs BMF (primary source, 80K+ orgs)
│   ├── propublica.py            # ProPublica Nonprofit API (financials)
│   ├── charity_nav.py           # Charity Navigator GraphQL (ratings, needs API key)
│   ├── va_facilities.py         # VA Lighthouse Facilities API (needs API key)
│   ├── va_vso.py                # VA VSO Accreditation Directory (web scrape)
│   ├── nrd.py                   # National Resource Directory (JSON API + sitemap)
│   └── nodc.py                  # Nonprofit Open Data Collective (broken, URL outdated)
│
├── loaders/                     # Data merging, deduplication, output
│   ├── __init__.py
│   ├── merger.py                # Multi-source merge with 7-source priority rules
│   ├── deduplicator.py          # 3-tier dedup: EIN exact → fuzzy name+city → URL domain
│   └── csv_writer.py            # Final CSV output + confidence scores + summary report
│
├── transformers/                # Data normalization and enrichment
│   ├── __init__.py
│   ├── normalizer.py            # EIN, phone, URL, address, state standardization
│   └── enricher.py              # Web scrape org websites for social/email
│
├── utils/                       # Utilities: HTTP, checkpointing
│   ├── __init__.py
│   ├── http_client.py           # RateLimitedSession with retry + disk cache
│   └── checkpoint.py            # Pickle-based save/resume for stages
│
├── data/
│   ├── raw/                     # Downloaded source files (gitignored)
│   ├── intermediate/            # Per-source parquet files (gitignored)
│   ├── checkpoints/             # Pickle checkpoints for each stage (gitignored)
│   ├── http_cache/              # Disk cache for HTTP requests (gitignored)
│   └── output/
│       ├── veteran_org_directory.csv     # MAIN OUTPUT: 80K+ orgs, 45 columns
│       ├── summary_report.txt            # Statistics and metadata report
│       ├── pipeline.log                  # Execution log
│       └── active_heroes/                # Filtered exports for stakeholder
│           ├── active_heroes_partners.csv
│           ├── vfw_partners.csv
│           └── ... (6 total)
│
├── .devcontainer/               # Dev container configuration
├── .git/                        # Git repository
├── .planning/                   # GSD planning documents
│   └── codebase/                # ARCHITECTURE.md, STRUCTURE.md, etc.
│
├── main.py                      # 8-stage pipeline orchestrator
├── app.py                       # Streamlit dashboard (6 tabs)
├── analyze_for_active_heroes.py # Strategic analysis + filtered CSVs for stakeholder
├── requirements.txt             # Streamlit + Pandas + Plotly (app only)
├── requirements-pipeline.txt    # Full pipeline deps (pandas, pyarrow, requests, beautifulsoup4, lxml, playwright, rapidfuzz, usaddress, tqdm, python-dotenv, aiohttp)
├── .env.example                 # Template for API keys (CHARITY_NAVIGATOR_API_KEY, VA_FACILITIES_API_KEY)
├── .gitignore                   # Excludes data/, __pycache__, .env
└── CLAUDE.md                    # Project guide (pipeline stages, known gaps, key decisions)
```

## Directory Purposes

**config/:**
- Purpose: Global configuration, schema definitions, and constant values
- Contains: Settings (API URLs, paths, rate limits), canonical 45-column schema with dtypes, NTEE category filters and veteran keyword list (119 keywords)
- Key files: `settings.py`, `schema.py`, `ntee_codes.py`

**extractors/:**
- Purpose: Extract data from 7 external sources
- Contains: Concrete extractor classes (one per source) inheriting from BaseExtractor; each implements `extract()` method and optionally overrides `transform()`
- Key files: `irs_bmf.py` (primary ~80K records), `propublica.py`, `va_vso.py`, `nrd.py`

**loaders/:**
- Purpose: Merge multi-source data, deduplicate, and write output
- Contains: Merger with priority-based field selection, 3-tier deduplicator, CSV writer with confidence scoring
- Key files: `merger.py`, `deduplicator.py`, `csv_writer.py`

**transformers/:**
- Purpose: Clean and standardize data formats; enrich with web scraping
- Contains: Normalizer for EIN/phone/URL/address formats; web enricher for social media extraction
- Key files: `normalizer.py`, `enricher.py`

**utils/:**
- Purpose: Shared infrastructure for HTTP requests and state management
- Contains: Rate-limited HTTP session with retries and disk cache; checkpoint save/load for resumable pipeline
- Key files: `http_client.py`, `checkpoint.py`

**data/:**
- Purpose: Data storage at all pipeline stages
- Contains: Raw downloads, intermediate parquets, checkpoints, HTTP cache, final CSV
- Note: All subdirectories except `output/` are gitignored

## Key File Locations

**Entry Points:**
- `main.py`: Pipeline orchestrator; run with `python main.py [--resume] [--clean] [--skip-enrichment] [--stages 1,5,8]`
- `app.py`: Streamlit dashboard; run with `streamlit run app.py`
- `analyze_for_active_heroes.py`: Stakeholder analysis export; run with `python analyze_for_active_heroes.py`

**Configuration:**
- `config/settings.py`: API URLs, file paths (PROJECT_ROOT, DATA_DIR, RAW_DIR, INTERMEDIATE_DIR, OUTPUT_DIR, CHECKPOINT_DIR), rate limits, timeout defaults, API key references
- `config/schema.py`: 45-column schema (SCHEMA_COLUMNS list), column names, dtypes, confidence weight dict (CONFIDENCE_WEIGHTS)
- `config/ntee_codes.py`: NTEE category filters, 119 veteran keyword list for filtering IRS BMF

**Core Logic:**
- `extractors/base_extractor.py`: Abstract class defining extract→transform→checkpoint pattern; all 7 sources inherit
- `loaders/merger.py`: SOURCE_PRIORITY list, `merge_all()` function orchestrating 7-source merge
- `loaders/deduplicator.py`: 3-tier dedup functions (_tier1_exact_ein, _tier2_fuzzy_name_city, _tier3_url_domain)
- `transformers/normalizer.py`: Normalization functions for EIN, phone, URL, address, state
- `utils/http_client.py`: RateLimitedSession class for rate-limited HTTP with caching and retries

**Testing:**
- None currently (no test directory; integration testing via pipeline execution with `--stages` flag)

## Naming Conventions

**Files:**
- Python modules: `snake_case.py` (e.g., `irs_bmf.py`, `base_extractor.py`)
- Directories: `lowercase_plural` (e.g., `extractors/`, `loaders/`, `transformers/`)
- Data outputs: Descriptive lowercase with underscores (e.g., `veteran_org_directory.csv`, `summary_report.txt`)

**Functions:**
- Private/internal: `_leading_underscore(param)` (e.g., `_tier1_exact_ein()`, `_merge_rows()`)
- Public: `snake_case(param)` (e.g., `normalize_ein()`, `merge_all()`, `deduplicate()`)
- Classes: `PascalCase` (e.g., `BaseExtractor`, `IrsBmfExtractor`, `RateLimitedSession`)

**Variables:**
- DataFrame/Series: `df`, `series_name` (e.g., `base_df`, `pp_df`, `filtered`)
- Dictionaries: `snake_case_dict` (e.g., `ein_sources`, `non_ein_sources`, `merge_map`)
- Primitives: `snake_case` (e.g., `rate_limit`, `min_interval`, `cache_key`)
- Constants: `UPPER_CASE` (e.g., `IRS_BMF_BASE_URL`, `CHECKPOINT_INTERVAL`)

**Types:**
- Type hints use `from __future__ import annotations` in all files for Python 3.9+ compatibility
- Union types: `type1 | type2` (e.g., `str | None`, `dict[str, pd.DataFrame]`)

## Where to Add New Code

**New Data Source (e.g., new VA API):**
1. Create `extractors/new_source.py` inheriting from `BaseExtractor`
2. Implement `extract()` method to fetch data
3. Implement `transform()` if needed to map to canonical schema
4. Add extractor to appropriate stage in `main.py` (likely stage 2–4)
5. Add source name to `SOURCE_PRIORITY` list in `loaders/merger.py`
6. Test with `python main.py --stages 1,YOUR_STAGE,5,6,8`

**New Column to Schema:**
1. Add tuple to `SCHEMA_COLUMNS` in `config/schema.py` (name, dtype, description)
2. Add weight to `CONFIDENCE_WEIGHTS` dict if it affects confidence score
3. Update extractors' `transform()` methods to populate new column
4. CSV writer will automatically include it

**New Dashboard Tab:**
1. Add tab name to `st.tabs()` list in `app.py`
2. Create `with tab_name:` block for content
3. Use filtered DataFrame (`filtered`) for data
4. Add Plotly charts via `st.plotly_chart(fig, use_container_width=True)`

**New Transformation/Normalization:**
1. Add function to `transformers/normalizer.py` or create new module in `transformers/`
2. Call from `normalize_dataframe()` in `main.py` stage 8
3. Use pattern: accept value or Series, return normalized value or Series

**New Utility Function:**
1. Add to `utils/` directory in appropriate module or create new `utils/new_util.py`
2. Follow existing import pattern: `from utils.checkpoint import load_checkpoint`

## Special Directories

**data/raw/:**
- Purpose: Stores downloaded source files (IRS BMF CSVs, Excel sheets from VA, JSON files from APIs)
- Generated: Yes (by extractors)
- Committed: No (gitignored)

**data/intermediate/:**
- Purpose: Parquet files for each source after extraction and transformation
- Generated: Yes (by BaseExtractor.run())
- Committed: No (gitignored)

**data/checkpoints/:**
- Purpose: Pickle files for resumable pipeline (one per stage)
- Generated: Yes (by checkpoint.save_checkpoint())
- Committed: No (gitignored)
- Naming: `extractor_{source_name}.pkl` (e.g., `extractor_irs_bmf.pkl`)

**data/http_cache/:**
- Purpose: Disk cache of HTTP responses (keyed by hash of method+URL+params)
- Generated: Yes (by RateLimitedSession)
- Committed: No (gitignored)
- Use case: Speed up development/testing by avoiding repeated API calls

**data/output/:**
- Purpose: Final artifacts (CSV, summary report, pipeline log, stakeholder exports)
- Generated: Yes (by csv_writer.py and analyze_for_active_heroes.py)
- Committed: No (gitignored, too large)
- Key file: `veteran_org_directory.csv` (input to Streamlit dashboard)

**.planning/codebase/:**
- Purpose: GSD architecture and structure documentation
- Generated: Yes (by GSD mappers)
- Committed: Yes
- Files: ARCHITECTURE.md, STRUCTURE.md, CONVENTIONS.md, TESTING.md, CONCERNS.md

---

*Structure analysis: 2026-02-11*

# Technology Stack

**Analysis Date:** 2026-02-11

## Languages

**Primary:**
- Python 3.9+ - ETL pipeline, data processing, and interactive web application
  - Uses `from __future__ import annotations` for Python 3.9+ type hint compatibility

## Runtime

**Environment:**
- Python 3.9 or higher (verified in pipeline code)

**Package Manager:**
- pip
- Lockfile: None (uses requirements-pipeline.txt and requirements.txt)

## Frameworks

**Core:**
- Streamlit 1.30+ - Interactive web dashboard for searching and filtering veteran organizations (`app.py`)
- Pandas 2.1+ - Primary data processing framework for ETL pipeline
- PyArrow 14.0+ - Columnar data format for intermediate storage

**Testing:**
- No test framework detected in requirements

**Build/Dev:**
- python-dotenv 1.0+ - Environment variable management
- Playwright 1.40+ - Headless browser automation for web scraping

## Key Dependencies

**Critical:**
- pandas 2.1+ - Data transformation, CSV read/write, and DataFrame operations
- requests 2.31+ - HTTP requests with retry logic and rate limiting for API calls
- streamlit 1.30+ - Web application framework with caching and real-time updates
- beautifulsoup4 4.12+ - HTML parsing for VA VSO and NRD web scraping
- plotly 5.18+ - Interactive charts and choropleth mapping in dashboard

**Data Processing:**
- PyArrow 14.0+ - Columnar storage in `data/intermediate/`
- rapidfuzz 3.5+ - Fuzzy string matching for deduplication
- usaddress 0.5.10+ - Address parsing and normalization
- tqdm 4.66+ - Progress bars for long-running operations

**Web Scraping:**
- beautifulsoup4 4.12+ - HTML parsing
- lxml 5.1+ - XML/HTML processing
- playwright 1.40+ - Browser automation
- aiohttp 3.9+ - Async HTTP client (prepared for future async expansion)

## Configuration

**Environment:**
- `.env.example` - Template for required environment variables
- Two distinct env vars required:
  - `CHARITY_NAVIGATOR_API_KEY` - Free API key from charitynavigator.org
  - `VA_FACILITIES_API_KEY` - Free API key from developer.va.gov
  - `LOG_LEVEL` - Logging verbosity (DEBUG, INFO, WARNING, ERROR; defaults to INFO)

**Build:**
- `config/settings.py` - Central config: URLs, rate limits, paths, API endpoints
  - Loads `.env` via `python-dotenv` at import time
  - All external service URLs and rate limits defined here

## Platform Requirements

**Development:**
- Python 3.9+
- macOS, Linux, or Windows
- ~500MB disk space for raw data downloads and intermediate files

**Production:**
- Deployed on Streamlit Community Cloud via GitHub (`vinceRM17/vet-org-directory`)
- Python 3.9+ runtime
- Requires `.env` configuration with API keys for full functionality

## Data Storage

**Formats:**
- CSV - Final output format for directory (`data/output/veteran_org_directory.csv`)
- Parquet - Intermediate storage (`data/intermediate/*.parquet`)
- JSON - Caching layer for HTTP responses in `data/http_cache/`
- Pickle - Pipeline checkpoints for resumability (`data/checkpoints/`)

**Local Directories:**
- `data/raw/` - Downloaded source files (IRS BMF CSVs)
- `data/intermediate/` - Per-source parquet files
- `data/output/` - Final CSV output and reports
- `data/http_cache/` - HTTP response cache (disk-based JSON)
- `data/checkpoints/` - Pickle files for resume capability

## Caching Strategy

**HTTP Caching:**
- Disk-based JSON cache in `data/http_cache/[source-name]/`
- Cache keys: SHA256 hash of method + URL + params
- Implemented in `utils/http_client.py` via `RateLimitedSession`
- Cache bypass: Use `use_cache=False` parameter in HTTP requests

**Streamlit Caching:**
- `@st.cache_data(ttl=300)` decorator on `load_data()` function in `app.py`
- 5-minute TTL ensures fresh CSV is picked up after deployment

## Rate Limiting

**Per-Source Limits (configured in `config/settings.py`):**
- IRS BMF: 1.0 req/sec
- ProPublica: 2.0 req/sec
- Charity Navigator GraphQL: 1.0 req/sec
- VA Facilities: 5.0 req/sec
- National Resource Directory: 0.5 req/sec
- VA VSO: 0.5 req/sec
- Web Enrichment: 0.5 req/sec

**Retry Policy:**
- Max 3 retries per request (DEFAULT_RETRIES in `config/settings.py`)
- Retry on: 429, 500, 502, 503, 504
- Exponential backoff multiplier: 1.0 seconds
- 30-second timeout per request (DEFAULT_TIMEOUT)

## Checkpointing

**Resumability:**
- Pickle-based checkpoints in `data/checkpoints/`
- Checkpoint interval: Every 500 API calls for API-intensive stages
- Supports `python main.py --resume` to continue from last checkpoint
- Clearing: `python main.py --clean` resets all checkpoints

---

*Stack analysis: 2026-02-11*

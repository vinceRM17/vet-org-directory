# External Integrations

**Analysis Date:** 2026-02-11

## APIs & External Services

**IRS Exempt Organizations Business Master File (BMF):**
- IRS SOI bulk CSV download (primary data source)
  - URL: `https://www.irs.gov/pub/irs-soi/eo[1-4].csv`
  - What it's used for: Initial list of 80K+ veteran organizations
  - Extractor: `extractors/irs_bmf.py`
  - No auth required (public data)
  - Files: eo1.csv, eo2.csv, eo3.csv, eo4.csv
  - Local cache: `data/raw/`

**ProPublica Nonprofit Explorer API:**
- REST API for nonprofit financial data enrichment
  - URL: `https://projects.propublica.org/nonprofits/api/v2`
  - What it's used for: Latest filing financials (revenue, expenses, assets) per EIN
  - SDK/Client: requests library (RateLimitedSession wrapper)
  - Rate limit: 2.0 requests/sec
  - Cache: `data/http_cache/propublica/`
  - Extractor: `extractors/propublica.py`
  - Auth: None (public API)
  - Stage: 2 (API Enrichment) - runs 5-8 hours for 80K+ EINs

**Charity Navigator GraphQL API:**
- GraphQL endpoint for org ratings and mission statements
  - URL: `https://api.charitynavigator.org/graphql`
  - What it's used for: Star ratings (0-4), overall scores, alerts/advisories, social media links, mission statements
  - SDK/Client: requests library (RateLimitedSession with JSON POST)
  - Auth: API key header `Charity-Navigator-Api-Key`
  - Env var: `CHARITY_NAVIGATOR_API_KEY`
  - Rate limit: 1.0 request/sec
  - Cache: `data/http_cache/charity_nav/`
  - Extractor: `extractors/charity_nav.py`
  - Status: Configured but requires free API key from charitynavigator.org
  - GraphQL Query: Queries `organizationByEIN` field with social media and advisory data

**VA Lighthouse Facilities API:**
- REST API for VA health, benefits, cemetery, and vet center facilities
  - URL: `https://api.va.gov/services/va_facilities/v1/facilities`
  - What it's used for: VA facility locations, services, contact information
  - SDK/Client: requests library (RateLimitedSession wrapper)
  - Auth: API key query parameter
  - Env var: `VA_FACILITIES_API_KEY`
  - Rate limit: 5.0 requests/sec
  - Cache: `data/http_cache/va_facilities/`
  - Extractor: `extractors/va_facilities.py`
  - Status: Configured but requires free API key from developer.va.gov
  - Facility types: health, benefits, cemetery, vet_center
  - Pagination: 200 records per page

**VA OGC VSO Accreditation Directory:**
- VA Office of General Counsel Veterans Service Officer accreditation lookup
  - URL: `https://www.va.gov/ogc/apps/accreditation/orgsexcellist.asp` (org dump)
  - URL: `https://www.va.gov/ogc/apps/accreditation/repexcellist.asp` (rep dump)
  - What it's used for: VA-accredited VSO organizations and representatives
  - SDK/Client: BeautifulSoup4 HTML parsing + requests
  - Rate limit: 0.5 requests/sec
  - Cache: `data/http_cache/va_vso/`
  - Extractor: `extractors/va_vso.py`
  - Auth: None (public search interface)
  - Data format: HTML tables converted to DataFrame

**National Resource Directory (NRD):**
- Vue.js SPA with JSON API endpoints for veteran support resources
  - URL: `https://www.nrd.gov` (base)
  - Endpoints: `/landingItems`, `/getSearchItems`, `/sitemap.xml`
  - What it's used for: Featured veteran resources, organization data, service categories
  - SDK/Client: requests + BeautifulSoup4 (XML sitemap parsing)
  - Rate limit: 0.5 requests/sec
  - Cache: `data/http_cache/nrd/`
  - Extractor: `extractors/nrd.py`
  - Auth: None (public API)
  - Strategy: Uses JSON API + sitemap discovery (HTML scraping doesn't work for SPA)
  - Coverage: ~7,900 resource URLs via sitemap

**Nonprofit Open Data Collective (NODC):**
- GitHub-hosted open datasets for nonprofit tax filings
  - Base URL: `https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file/master`
  - What it's used for: Mission statements, program descriptions, employee/volunteer counts
  - SDK/Client: requests (download via RateLimitedSession)
  - Rate limit: 2.0 requests/sec
  - Cache: `data/http_cache/nodc/`
  - Extractor: `extractors/nodc.py`
  - Auth: None (public GitHub repository)
  - Data format: CSV downloads (concordance file and master records)
  - Status: Known issue - GitHub URLs have changed; file locations need updates
  - Attempted files:
    - `concordance.csv` (field mappings)
    - `bmf-master.csv` or `990_master.csv` (org data)

## Data Storage

**Output Format:**
- Primary: CSV at `data/output/veteran_org_directory.csv`
  - 80,784 organizations
  - 45+ columns per `config/schema.py`
  - CSV compatible with Excel, Pandas, most BI tools

**Intermediate Storage:**
- Parquet files in `data/intermediate/` (one per extractor)
- Format: Apache Parquet via PyArrow
- Purpose: Efficient columnar storage between pipeline stages
- Reduced memory footprint vs. CSV

**Caching:**
- File storage: Local filesystem
- No database backend (purely file-based pipeline)
- Cache location: `data/http_cache/` (organized by source name)
- Format: JSON (wrapped HTTP responses)

## Authentication & Identity

**Auth Provider:**
- Custom (no centralized auth provider)

**API Keys Required:**
- CHARITY_NAVIGATOR_API_KEY - Free registration at charitynavigator.org
- VA_FACILITIES_API_KEY - Free registration at developer.va.gov
- Configured via `.env` file at project root (gitignored)
- No authentication for: IRS BMF, ProPublica, VA VSO, NRD, NODC (all public endpoints)

**Other Integrations:**
- Streamlit Cloud deployment with GitHub authentication (OAuth)
  - Repo: `vinceRM17/vet-org-directory`
  - Branch: main (auto-deploys on push)

## Monitoring & Observability

**Error Tracking:**
- None detected (no Sentry, Rollbar, or similar)

**Logs:**
- File-based: `data/output/pipeline.log` (created by main.py)
- Format: `%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s`
- Console output to stdout (dual logging)
- Level: Configurable via `LOG_LEVEL` env var (defaults to INFO)
- Rotation: None (single file appends)

**Progress Tracking:**
- tqdm progress bars in terminal for long-running operations
- Checkpoint logging every 500 API calls for resumable stages

## CI/CD & Deployment

**Hosting:**
- Streamlit Community Cloud (free tier)
- URL: Deployed from GitHub repository
- Live dashboard: Interactive web UI with Streamlit

**CI Pipeline:**
- None detected (no GitHub Actions, GitLab CI, etc.)
- Manual deployment: Push to main branch triggers Streamlit Cloud redeploy
- Automatic on push: Streamlit Cloud watches GitHub repo

**Local Pipeline Execution:**
- Command: `python main.py [flags]`
- Full run: ~30-50 hours (8-stage pipeline)
- Resumable: `python main.py --resume` continues from last checkpoint
- Selective: `python main.py --stages 1,5,6,8` runs only specified stages
- Skip enrichment: `python main.py --skip-enrichment` omits Stage 7 (web scraping)

## Environment Configuration

**Required env vars (for full functionality):**
- `CHARITY_NAVIGATOR_API_KEY` - Optional (Stage 2 skips if not set)
- `VA_FACILITIES_API_KEY` - Optional (Stage 4 skips if not set)
- `LOG_LEVEL` - Optional (defaults to INFO)

**Optional env vars:**
- None detected beyond the above

**Secrets location:**
- `.env` file at project root (gitignored)
- Template: `.env.example`
- No secrets checked into git

**Configuration files:**
- `config/settings.py` - All URLs, rate limits, paths, API endpoints
- `config/ntee_codes.py` - NTEE classification filters and veteran keywords
- `config/schema.py` - 45-column DataFrame schema and coercion rules

## Webhooks & Callbacks

**Incoming:**
- None detected

**Outgoing:**
- None detected

## Data Pipeline Stages

**Overview (8-stage ETL):**

| Stage | Name | Duration | Dependencies | Data Source |
|-------|------|----------|--------------|-------------|
| 1 | IRS BMF Download + Filter | ~15 min | None | IRS SOI (public CSVs) |
| 2 | API Enrichment | ~5-8 hrs | Stage 1 | ProPublica + Charity Navigator |
| 3 | Web Scraping | ~1 hr | None | VA VSO (HTTP) + NRD (JSON API) |
| 4 | Additional Sources | ~30 min | Stage 1 | VA Facilities API + NODC |
| 5 | Merge All Sources | ~5 min | Stages 1-4 | DataFrame union + column mapping |
| 6 | Deduplication | ~15 min | Stage 5 | 3-tier: EIN → fuzzy name+city → URL domain |
| 7 | Web Enrichment | ~10-20 hrs | Stage 6 | Web scraping for emails/social (SKIPPED by default) |
| 8 | CSV Output + Report | ~2 min | Stages 6/7 | Final CSV + summary report |

**Checkpoint Architecture:**
- Extractors save results to parquet after transform
- API stages checkpoint every 500 calls (resumability)
- Final stage writes CSV and summary report to `data/output/`

## Data Quality & Deduplication

**Deduplication Strategy (3-tier):**
1. **Tier 1 - Exact EIN match**: Merge rows with identical EIN, keep most complete fields
2. **Tier 2 - Fuzzy name+city**: Use rapidfuzz for near-match detection (threshold configurable)
3. **Tier 3 - URL domain**: Extract domain from website URL and deduplicate by domain

**Confidence Scoring:**
- Per-field confidence weights in `config/schema.py`
- Applied by merger and deduplicator to select best data when conflicts exist

---

*Integration audit: 2026-02-11*

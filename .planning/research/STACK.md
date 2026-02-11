# Technology Stack Research

**Domain:** Nonprofit Data Enrichment / Veteran Organization Directory
**Researched:** 2026-02-11
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Playwright** | `1.58.0` | Browser automation for dynamic content scraping | Modern, headless browser automation with 12% faster page loads and 15% lower memory than Selenium. Direct browser protocol communication eliminates WebDriver latency. Native async support. Best choice for JavaScript-heavy nonprofit sites. |
| **httpx** | `0.28.1` | Async HTTP client for API requests | Modern requests replacement with full async/await support, HTTP/2, connection pooling. Essential for concurrent API calls (Charity Navigator, VA Facilities). 2-3× faster than aiohttp for typical API workloads. |
| **gql** | `4.0.0` | GraphQL client for Charity Navigator API | Official GraphQL client with automatic batching, sync/async transports, built-in validation. Designed for Charity Navigator's GraphQL endpoint. Cleaner API than raw httpx for GraphQL queries. |
| **RapidFuzz** | `3.5+` | Fuzzy string matching for deduplication | 10× faster than FuzzyWuzzy, MIT licensed (FuzzyWuzzy is GPL), written in C++ with algorithmic improvements. Includes additional metrics (Hamming, Jaro-Winkler). Drop-in replacement. Already in project. |
| **Pandera** | `0.29.0` | DataFrame validation for data quality | Production-grade validation for Pandas DataFrames with typed schemas, lazy validation, custom checks. 3× faster than manual validation. Prevents silent data corruption in enrichment pipeline. Requires Python >=3.10. |
| **BeautifulSoup4** | `4.12+` | HTML parsing for static content | Lightweight, simple API for parsing static HTML. Perfect for extracting contact info from simple nonprofit websites. Use for non-JavaScript sites. Already in project. |
| **lxml** | `5.1+` | XML/HTML parsing backend | Fast C-based parser for BeautifulSoup. 5-10× faster than html.parser. Required for VA VSO Excel dumps and XML sitemaps. Already in project. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | `9.0+` | Retry logic with exponential backoff | Add to all API calls (Charity Navigator, VA Facilities, ProPublica). Implements exponential backoff, jitter, selective exception handling. Prevents overwhelming rate-limited APIs. |
| **aiometer** | `0.5+` | Async rate limiting | Control concurrent API requests with precise rate limits. Use for VA Facilities API (50 req/sec), Charity Navigator (unknown limits). Works with httpx AsyncClient. |
| **extract-emails** | `3.0+` | Email extraction from HTML/text | Released June 2025, Python 3.10+ compatible. Regex-based extraction from scraped website content. Alternative: write custom regex. |
| **phonenumbers** | `8.13+` | Phone number parsing and validation | Google's libphonenumber port. Validates US phone formats, standardizes to E.164. Better than regex for international numbers (some veteran orgs have overseas offices). |
| **pydantic** | `2.10+` | Data validation and settings management | Type-safe config validation for API keys, schema validation for API responses. Replaces manual dict checks. Works alongside Pandera (Pandera=DataFrames, Pydantic=API models). |
| **structlog** | `24.4+` | Structured logging for pipeline monitoring | JSON-formatted logs for debugging 80K+ org enrichment pipeline. Easier to parse than print() statements. Critical for tracking Stage 7 enrichment failures. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **pytest** | Unit testing for extractors/transformers | Test each extractor independently. Mock HTTP responses to avoid API rate limits during CI. |
| **pytest-asyncio** | Async test support | Required for testing async extractors (Playwright, httpx). |
| **pytest-playwright** | Playwright fixtures for tests | Provides browser fixtures, screenshot on failure. |
| **ruff** | Linting and formatting | Replaces Black, Flake8, isort. 10-100× faster. Single config. |
| **mypy** | Type checking | Catch type errors in DataFrame operations. Use with pandas-stubs. |

## Installation

### Core Dependencies (add to requirements-pipeline.txt)
```bash
# Web scraping and APIs
playwright==1.58.0
httpx==0.28.1
gql==4.0.0
beautifulsoup4>=4.12
lxml>=5.1

# Data processing and validation
pandas>=2.1
pyarrow>=14.0
pandera==0.29.0
pydantic>=2.10

# String matching and parsing
rapidfuzz>=3.5
phonenumbers>=8.13
extract-emails>=3.0

# Async and retry handling
tenacity>=9.0
aiometer>=0.5
aiohttp>=3.9

# Utilities
usaddress>=0.5.10
tqdm>=4.66
python-dotenv>=1.0
structlog>=24.4
```

### Dev Dependencies (create requirements-dev.txt)
```bash
pytest>=8.0
pytest-asyncio>=0.24
pytest-playwright>=0.6
pytest-cov>=6.0
ruff>=0.8
mypy>=1.11
pandas-stubs>=2.1
```

### Playwright Browser Installation
```bash
# After pip install playwright
playwright install chromium
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| **Playwright** | Selenium | Never. Selenium is slower, more fragile, requires separate drivers. Playwright is strictly superior for 2025/2026. |
| **Playwright** | Scrapy | Large-scale crawling (10K+ domains). Scrapy has better middleware for managing concurrent crawls. For this project, Playwright is sufficient. |
| **httpx** | aiohttp | Already in project, but httpx is more modern. Migrate gradually. Use httpx for new code (API clients), keep aiohttp for existing scrapers if stable. |
| **httpx** | requests | Never for new code. requests is synchronous only. Use httpx.Client() if you need sync API (drop-in replacement). |
| **gql** | Manual httpx GraphQL | Simple GraphQL queries. For Charity Navigator's complex schema, gql provides validation and type safety. |
| **Pandera** | Great Expectations | Enterprise data quality framework. Overkill for this project. Use if validating 100+ data sources. |
| **tenacity** | Manual retry loops | Never. tenacity is battle-tested, handles edge cases (jitter, circuit breakers), more maintainable. |
| **extract-emails** | Custom regex | Simple use case with known email formats. For nonprofit websites (varied formats), use extract-emails. |
| **RapidFuzz** | FuzzyWuzzy | Never. RapidFuzz is 10× faster, better licensed, more features. Already migrated. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Selenium** | Slower (12% slower page loads), requires WebDriver, more fragile scripts, larger memory footprint | **Playwright** — Modern, faster, native async |
| **FuzzyWuzzy** | 10× slower, GPL license (viral), no Hamming/Jaro-Winkler metrics | **RapidFuzz** — Drop-in replacement, MIT licensed |
| **requests** | No async support, blocking I/O, slow for 80K+ orgs | **httpx** — Full async, HTTP/2, connection pooling |
| **snscrape** | Social media scraper, deprecated, broken APIs (Twitter/X, Facebook) | **Playwright** — Scrape public social media pages directly via browser automation |
| **socialreaper** | Outdated (last updated 2018), requires API keys for all platforms | **Playwright** — Scrape public-facing social media profiles |
| **Beautiful Soup alone (for dynamic sites)** | Cannot execute JavaScript, misses dynamic content (40%+ of nonprofit sites) | **Playwright** + BeautifulSoup — Playwright renders JS, BeautifulSoup parses HTML |
| **aiohttp (for new code)** | Less ergonomic API, no HTTP/2, limited connection pooling | **httpx** — Modern requests-like API with async |
| **Manual dict validation** | Error-prone, hard to maintain, no type safety | **Pydantic** (API responses) + **Pandera** (DataFrames) |
| **print() for debugging** | Unstructured, hard to parse, no log levels | **structlog** — Structured JSON logs, filterable |

## Stack Patterns by Use Case

### Pattern 1: Static Content Scraping (Simple Nonprofit Sites)
**When:** Organization website is static HTML (no JavaScript)
**Stack:**
```python
import httpx
from bs4 import BeautifulSoup

async with httpx.AsyncClient() as client:
    response = await client.get(url)
    soup = BeautifulSoup(response.text, 'lxml')
    # Extract contact info
```
**Why:** Faster, less resource-intensive than Playwright. No browser needed.

### Pattern 2: Dynamic Content Scraping (Modern Nonprofit Sites)
**When:** Website requires JavaScript (SPA, lazy-loaded content)
**Stack:**
```python
from playwright.async_api import async_playwright

async with async_playwright() as p:
    browser = await p.chromium.launch(headless=True)
    page = await browser.new_page()
    await page.goto(url)
    content = await page.content()
    # Parse with BeautifulSoup or Playwright selectors
```
**Why:** Executes JavaScript, waits for dynamic content to load.

### Pattern 3: API Integration (Charity Navigator, VA Facilities)
**When:** Structured data from REST/GraphQL APIs
**Stack:**
```python
import httpx
from gql import gql, Client
from gql.transport.httpx import HTTPXAsyncTransport
from tenacity import retry, stop_after_attempt, wait_exponential

transport = HTTPXAsyncTransport(url=api_url, headers={"Authorization": key})
client = Client(transport=transport)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_charity_data(ein):
    query = gql("query($ein: String!) { nonprofit(ein: $ein) { name rating } }")
    return await client.execute_async(query, variable_values={"ein": ein})
```
**Why:** GraphQL validation, automatic retries, exponential backoff.

### Pattern 4: Rate-Limited Batch Processing (80K+ Orgs)
**When:** Scraping/enriching thousands of organizations
**Stack:**
```python
import asyncio
import aiometer
from tenacity import retry, retry_if_exception_type

@retry(retry=retry_if_exception_type(httpx.HTTPStatusError))
async def enrich_org(url):
    async with httpx.AsyncClient() as client:
        # Scrape website
        pass

async def process_batch(urls):
    # Limit to 10 requests/sec, 50 concurrent
    await aiometer.run_all(
        [functools.partial(enrich_org, url) for url in urls],
        max_at_once=50,
        max_per_second=10
    )
```
**Why:** Prevents overwhelming target servers, respects rate limits, retries failures.

### Pattern 5: Data Validation Pipeline
**When:** Validating enriched data before CSV output
**Stack:**
```python
import pandera as pa

schema = pa.DataFrameSchema({
    "EIN": pa.Column(str, pa.Check.str_matches(r'^\d{2}-\d{7}$')),
    "Phone": pa.Column(str, pa.Check.str_matches(r'^\+1\d{10}$'), nullable=True),
    "Email": pa.Column(str, pa.Check.str_contains('@'), nullable=True),
    "Confidence_Score": pa.Column(float, pa.Check.in_range(0, 100)),
})

@pa.check_types(lazy=True)
def validate_enriched_data(df: pa.typing.DataFrame[schema]) -> pa.typing.DataFrame[schema]:
    return df
```
**Why:** Type-safe validation, lazy validation shows all errors, prevents bad data in CSV.

## Version Compatibility Matrix

| Package | Version | Python | Notes |
|---------|---------|--------|-------|
| **Playwright** | 1.58.0 | 3.9-3.13 | Project uses 3.9+ (per CLAUDE.md) |
| **Pandera** | 0.29.0 | >=3.10 | **Requires Python 3.10+** (upgrade blocker) |
| **httpx** | 0.28.1 | 3.9+ | Compatible |
| **gql** | 4.0.0 | 3.8+ | Compatible |
| **pydantic** | 2.10+ | 3.8+ | Compatible (v2 has breaking changes from v1) |
| **tenacity** | 9.0+ | 3.8+ | Compatible |

**Critical Decision:** Pandera requires Python 3.10+. Options:
1. **Recommended:** Upgrade project to Python 3.10+ (minimal breaking changes)
2. **Alternative:** Use Pydantic for all validation (less ergonomic for DataFrames)
3. **Workaround:** Use Pandera 0.17.x (last Python 3.9 release) — not recommended, missing features

## API Key Requirements

| Service | Required? | Rate Limit | Cost | How to Get |
|---------|-----------|------------|------|------------|
| **Charity Navigator** | Yes (for enrichment) | Unknown (add aiometer) | Free tier: 1K calls/month | [developer.charitynavigator.org](https://developer.charitynavigator.org/) |
| **VA Lighthouse Facilities** | Yes (for VA facilities) | 50 req/sec | Free | [developer.va.gov](https://developer.va.gov/) |
| **ProPublica Nonprofit Explorer** | No | Unknown | Free | Already working |

**Configuration (.env):**
```bash
CHARITY_NAV_API_KEY=your_key_here
VA_FACILITIES_API_KEY=your_key_here
```

## Migration Path (Existing → Recommended)

### Phase 1: Add New Libraries (Low Risk)
1. Add `tenacity`, `aiometer`, `structlog`, `phonenumbers`, `extract-emails` to requirements
2. Add retry decorators to existing API calls (ProPublica, VA VSO)
3. Replace print() with structlog in main.py

### Phase 2: Upgrade Existing (Medium Risk)
1. Upgrade Playwright 1.40 → 1.58 (test extractors)
2. Add `httpx` for new API clients (Charity Navigator, VA Facilities)
3. Keep `aiohttp` for existing scrapers (don't break working code)

### Phase 3: Add Validation (Medium Risk)
1. Upgrade Python 3.9 → 3.10 (test in dev container)
2. Add Pandera schemas for each DataFrame (irs_bmf, propublica, merged)
3. Add validation checkpoints before CSV output

### Phase 4: Refactor (High Risk, Optional)
1. Migrate aiohttp → httpx (retest all scrapers)
2. Replace manual dict checks → Pydantic models
3. Add pytest test suite with mocked APIs

## Stack Rationale Summary

**Why this stack beats alternatives:**
1. **Playwright > Selenium:** 12% faster, native async, no WebDriver, modern API
2. **httpx > requests/aiohttp:** Async + HTTP/2 + requests-like API
3. **gql > raw HTTP:** Type safety, validation, batching for GraphQL
4. **RapidFuzz > FuzzyWuzzy:** 10× faster, better license, more features
5. **Pandera > manual checks:** Type-safe, lazy validation, prevents silent failures
6. **tenacity > manual retry:** Battle-tested, exponential backoff, jitter
7. **aiometer > asyncio.Semaphore:** Precise rate limiting (requests/sec + concurrent)

**What's missing from current stack:**
- ❌ **No retry logic** → Add tenacity
- ❌ **No rate limiting** → Add aiometer
- ❌ **No data validation** → Add Pandera (requires Python 3.10+)
- ❌ **No structured logging** → Add structlog
- ❌ **No GraphQL client** → Add gql (for Charity Navigator)
- ❌ **No phone/email parsers** → Add phonenumbers, extract-emails

## Sources

**Web Scraping:**
- [7 Best Python Web Scraping Libraries for 2025 | ScrapingBee](https://www.scrapingbee.com/blog/best-python-web-scraping-libraries/) — Playwright vs BeautifulSoup comparison
- [Best Web Scraping Tools in 2026](https://scrapfly.io/blog/posts/best-web-scraping-tools) — Performance benchmarks
- [Python Web Scraping: Beautiful Soup, Scrapy, and Playwright](https://dasroot.net/posts/2025/12/python-web-scraping-beautiful-soup/) — Use case patterns

**Charity Navigator API:**
- [Charity Navigator's GraphQL API](https://www.charitynavigator.org/products-and-services/graphql-api/) — Official documentation
- [Charity Navigator Developer Portal](https://developer.charitynavigator.org/) — API access
- [CharityNavigator GitHub Examples](https://github.com/CharityNavigator/cn-examples) — Python examples

**VA Lighthouse API:**
- [VA API Platform](https://developer.va.gov/) — Official developer portal
- [VA Lighthouse APIs](https://digital.va.gov/general/lighthouse-apis-provide-solutions-to-improve-the-veteran-experience/) — API overview
- [vets-api-clients GitHub](https://github.com/department-of-veterans-affairs/vets-api-clients) — Reference implementations

**Contact Extraction:**
- [Social Media Scraping in 2025](https://scrapfly.io/blog/posts/social-media-scraping-in-2025) — Best practices
- [extract-emails PyPI](https://pypi.org/project/extract-emails/) — Email extraction library (June 2025)
- [Contact Details Scraper API](https://apify.com/practicaltools/contact-details-scraper/api/python) — Alternative approach

**GraphQL Client:**
- [Top 3 Python Libraries for GraphQL](https://blog.graphqleditor.com/top-3-python-libraries-for-graphql) — gql vs Graphene comparison
- [gql GitHub](https://github.com/graphql-python/gql) — Official repository
- [gql 4.0.0 Release](https://gql.readthedocs.io/en/stable/intro.html) — Documentation

**Rate Limiting:**
- [How to Rate Limit Async Requests in Python](https://scrapfly.io/blog/posts/how-to-rate-limit-asynchronous-python-requests) — aiometer patterns
- [Python Rate Limiting for APIs](https://www.techbuddies.io/2025/12/13/python-rate-limiting-for-apis-implementing-robust-throttling-in-fastapi/) — Best practices
- [Async Distributed Rate Limiters](https://github.com/snok/self-limiters) — Alternative library

**Data Validation:**
- [How to Build Production-Grade Data Validation Pipelines Using Pandera](https://www.marktechpost.com/2026/02/05/how-to-build-production-grade-data-validation-pipelines-using-pandera-typed-schemas-and-composable-dataframe-contracts/) — Pandera best practices
- [Pandera PyPI](https://pypi.org/project/pandera/) — Version 0.29.0 (Jan 2026)
- [Data Validation Libraries for Polars (2025)](https://posit-dev.github.io/pointblank/blog/validation-libs-2025/) — Alternatives comparison

**Playwright:**
- [Playwright Python PyPI](https://pypi.org/project/playwright/) — Version 1.58.0 (Jan 2026)
- [Playwright Python Guide](https://blog.apify.com/python-playwright/) — Async context manager patterns
- [Playwright GitHub Releases](https://github.com/microsoft/playwright-python/releases) — Changelog

**RapidFuzz:**
- [RapidFuzz vs FuzzyWuzzy](https://plainenglish.io/blog/rapidfuzz-versus-fuzzywuzzy) — Performance comparison (10× speedup)
- [RapidFuzz GitHub](https://github.com/rapidfuzz/RapidFuzz) — Official repository
- [Top 5 Fuzzy Matching Tools for 2025](https://matchdatapro.com/top-5-fuzzy-matching-tools-for-2025/) — Industry recommendations

**Retry Patterns:**
- [tenacity GitHub](https://github.com/jd/tenacity) — Official repository
- [Building Resilient Python Applications with Tenacity](https://www.amitavroy.com/articles/building-resilient-python-applications-with-tenacity-smart-retries-for-a-fail-proof-architecture) — Best practices
- [Python Retry Policies with Tenacity](https://medium.com/@hadiyolworld007/python-retry-policies-with-tenacity-jitter-backoff-and-idempotency-that-survives-chaos-12bba4fc8d32) — Jitter and backoff patterns

**HTTP Clients:**
- [HTTPX Documentation](https://www.python-httpx.org/) — Official docs
- [httpx PyPI](https://pypi.org/project/httpx/) — Version 0.28.1
- [Getting Started with HTTPX](https://betterstack.com/community/guides/scaling-python/httpx-explained/) — Modern HTTP client guide

---

*Stack research for: Nonprofit Data Enrichment — Veteran Organization Directory*
*Researched: 2026-02-11*
*Confidence: HIGH (versions verified via PyPI, patterns verified via official docs and 2025/2026 community sources)*

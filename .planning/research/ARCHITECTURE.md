# Architecture Research

**Domain:** Nonprofit Data Enrichment / Web Scraping Contact Discovery
**Researched:** 2026-02-11
**Confidence:** HIGH

## Standard Architecture

### System Overview

Data enrichment systems for nonprofit contact discovery typically follow a multi-stage pipeline architecture with three primary layers:

```
┌─────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                       │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Stage      │  │   Checkpoint  │  │   Failover   │        │
│  │  Manager    │  │   Manager     │  │   Manager    │        │
│  └─────┬──────┘  └──────┬───────┘  └──────┬───────┘        │
├────────┴─────────────────┴──────────────────┴───────────────┤
│                    ENRICHMENT LAYER                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │  Web      │  │  Social   │  │  Email    │  │   API     │  │
│  │  Scraper  │  │  Media    │  │  Finder   │  │  Client   │  │
│  │          │  │  Crawler  │  │           │  │           │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
├───────┴──────────────┴─────────────┴─────────────┴──────────┤
│                  INFRASTRUCTURE LAYER                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Rate Limiter   │  │  Cache      │  │  Queue      │     │
│  │  + Retry Logic  │  │  Manager    │  │  Manager    │     │
│  └─────────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **Orchestration Layer** | Manages stage execution, checkpointing, failover strategies | Python main.py with argparse for CLI control |
| **Stage Manager** | Coordinates multi-stage pipeline execution with resume capability | Function-based stage execution (stage1_irs, stage2_api, etc.) |
| **Checkpoint Manager** | Saves progress at intervals; enables resumability | Pickle-based snapshots + parquet intermediate files |
| **Failover Manager** | Implements waterfall enrichment across multiple data providers | Sequential provider polling with 85-95% success rates |
| **Web Scraper** | Fetches HTML content for contact extraction | BeautifulSoup for static sites; Playwright for JS-heavy sites |
| **Social Media Crawler** | Discovers social media profiles from website HTML/meta | Regex pattern matching + third-party scraping APIs |
| **Email Finder** | Extracts and validates email addresses from web content | Regex extraction + SKIP_EMAILS filter + verification APIs |
| **API Client** | Integrates with external enrichment APIs (ProPublica, etc.) | RateLimitedSession with retry logic + disk cache |
| **Rate Limiter** | Controls request frequency to avoid 429 errors | Token bucket pattern with exponential backoff (1s → 2s → 4s) |
| **Cache Manager** | Stores HTTP responses to disk to avoid re-fetching | SHA256 hashed keys + JSON serialization |
| **Queue Manager** | Controls request flow for large-scale scraping jobs | Request queues limiting to ~30 requests/minute |

## Recommended Project Structure

```
transformers/
├── enricher.py              # Web enrichment coordinator
├── contact_discovery/       # Contact discovery components
│   ├── __init__.py
│   ├── web_scraper.py       # HTML fetching + parsing
│   ├── email_extractor.py   # Email pattern matching + validation
│   ├── phone_extractor.py   # Phone normalization + extraction
│   └── social_finder.py     # Social media URL discovery
├── api_integration/         # Multi-API orchestration
│   ├── __init__.py
│   ├── waterfall.py         # Waterfall enrichment pattern
│   ├── providers/           # Individual API integrations
│   │   ├── clearbit.py
│   │   ├── hunter.py
│   │   ├── apollo.py
│   │   └── peopledatalabs.py
│   └── validators/          # Data quality checks
│       ├── email_validator.py
│       └── phone_validator.py
utils/
├── http_client.py           # Rate-limited HTTP with retry + cache
├── queue_manager.py         # Request queue for scale
├── checkpoint.py            # Resumability for long-running jobs
└── proxy_manager.py         # Proxy rotation for scale (future)
config/
├── enrichment_settings.py   # Rate limits, timeouts, API keys
└── provider_priority.py     # Waterfall provider order
```

### Structure Rationale

- **transformers/enricher.py**: Single coordinator for Stage 7 enrichment; delegates to specialized components
- **contact_discovery/**: Isolates web scraping logic from API integration; easier to swap BeautifulSoup for Playwright
- **api_integration/waterfall.py**: Implements failover pattern where Provider A → B → C until data found
- **providers/**: One file per API; enables parallel development and easy addition of new sources
- **validators/**: Separates data quality from extraction; critical for maintaining 97%+ accuracy
- **utils/http_client.py**: Centralized rate limiting + caching prevents scattered retry logic

## Architectural Patterns

### Pattern 1: Waterfall Enrichment (Failover)

**What:** Sequential routing through multiple data providers until target field (email, phone) is found. If Provider A fails or returns no data, automatically try Provider B, then C, maximizing match rates (85-95% vs 50-60% single-provider).

**When to use:** When enriching contacts at scale with multiple paid/free APIs available. Essential for Kentucky subset enrichment where contact data is sparse.

**Trade-offs:**
- **Pro**: Dramatically higher success rates; cost-efficient (stops when found)
- **Pro**: Built-in redundancy (99.99% uptime even if providers go down)
- **Con**: Increased complexity in orchestration logic
- **Con**: Latency accumulation if multiple providers timeout

**Example:**
```python
# transformers/api_integration/waterfall.py
class WaterfallEnricher:
    def __init__(self, providers: list[BaseProvider]):
        self.providers = providers  # Ordered by priority/cost

    def enrich_email(self, org_name: str, domain: str) -> str | None:
        for provider in self.providers:
            try:
                result = provider.find_email(org_name, domain)
                if result and self._validate_email(result):
                    logger.info(f"Found via {provider.name}")
                    return result
            except Exception as e:
                logger.debug(f"{provider.name} failed: {e}")
                continue  # Failover to next provider
        return None  # All providers exhausted
```

### Pattern 2: Checkpoint-Based Resumability

**What:** Saves pipeline state at regular intervals (e.g., every 500 records) to disk. On failure, resumes from last checkpoint instead of restarting entire job. Critical for 10-20 hour enrichment runs.

**When to use:** Any ETL stage that processes >1000 records or runs >1 hour. Mandatory for web scraping stages.

**Trade-offs:**
- **Pro**: Prevents lost work on crashes/interruptions
- **Pro**: Enables partial re-runs (e.g., --stages 7,8 --resume)
- **Con**: Disk I/O overhead every N records
- **Con**: Checkpoint files can grow large (mitigate with parquet compression)

**Example:**
```python
# transformers/enricher.py (existing pattern)
def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
    partial = load_checkpoint("enricher_partial")
    if partial is not None:
        enrichments, done_indices = partial
        self.logger.info(f"Resuming from {len(done_indices)} completed")
    else:
        enrichments = {}
        done_indices = set()

    for count, idx in enumerate(remaining):
        # ... enrichment logic ...
        done_indices.add(idx)

        if (count + 1) % CHECKPOINT_INTERVAL == 0:
            save_checkpoint("enricher_partial", (enrichments, done_indices))
```

### Pattern 3: Rate Limiting with Exponential Backoff

**What:** Controls request frequency to external APIs/websites. On 429 errors, waits exponentially longer (1s → 2s → 4s → 8s) before retrying. Prevents IP bans and respects server limits.

**When to use:** All HTTP requests to external systems. Non-negotiable for web scraping and API enrichment.

**Trade-offs:**
- **Pro**: Prevents rate limit violations (429 errors, IP bans)
- **Pro**: Automatic retry increases success rates
- **Con**: Slows throughput (but necessary for compliance)
- **Con**: Can add significant time to large jobs

**Example:**
```python
# utils/http_client.py (existing implementation)
class RateLimitedSession:
    def _wait_for_rate_limit(self):
        if self.min_interval > 0:
            elapsed = time.time() - self._last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
        self._last_request_time = time.time()

    def get(self, url: str, use_cache: bool = True, **kwargs):
        # Check cache first
        if use_cache and self._cache_dir:
            cached = self._get_cached(key)
            if cached is not None:
                return cached

        # Rate limit enforcement
        self._wait_for_rate_limit()

        # Retry with backoff (via urllib3.util.retry)
        resp = self.session.get(url, **kwargs)
        return resp
```

### Pattern 4: BeautifulSoup + Playwright Composition

**What:** Use BeautifulSoup for static HTML parsing (fast, low memory); swap to Playwright for JavaScript-heavy sites requiring browser rendering. Compositional approach optimizes for speed vs capability.

**When to use:** BeautifulSoup for 90% of nonprofit websites (static HTML); Playwright for modern SPAs (React/Vue) or sites with heavy JS.

**Trade-offs:**
- **Pro**: BeautifulSoup is 10x faster than headless browsers for static sites
- **Pro**: Playwright handles JS-rendered content that BeautifulSoup misses
- **Con**: Switching between tools adds code complexity
- **Con**: Playwright requires more memory (50-100MB per browser instance)

**Example:**
```python
# transformers/contact_discovery/web_scraper.py
def scrape_website(url: str, use_playwright: bool = False) -> dict:
    if use_playwright:
        # For JS-heavy sites
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            html = page.content()
            browser.close()
    else:
        # For static sites (default)
        resp = http_client.get(url, use_cache=True)
        html = resp.text

    soup = BeautifulSoup(html, "lxml")
    return extract_contacts(soup)
```

## Data Flow

### Request Flow: Kentucky Subset Enrichment

```
[Stage 7: Web Enrichment Triggered]
    ↓
[Filter: Kentucky orgs only] ← (state == "KY") from merged dataset
    ↓
[For each org with website but missing contact info]
    ↓
┌─────────────────────────────────────────────┐
│  PRIMARY PATH: Direct Web Scraping          │
├─────────────────────────────────────────────┤
│  Web Scraper (BeautifulSoup)                │
│    → Fetch HTML via RateLimitedSession      │
│    → Extract email (regex patterns)         │
│    → Extract social URLs (SOCIAL_PATTERNS)  │
│    → Extract meta description → mission     │
│  Cache hit? Return cached → Skip HTTP       │
│  Rate limit? Wait with exponential backoff  │
└──────────────┬──────────────────────────────┘
               ↓
┌─────────────────────────────────────────────┐
│  FALLBACK PATH: Waterfall API Enrichment    │
├─────────────────────────────────────────────┤
│  IF email still missing:                    │
│    Provider 1 (Hunter.io) → find_email()    │
│    IF fail → Provider 2 (Clearbit)          │
│    IF fail → Provider 3 (Apollo)            │
│  STOP when verified email found             │
└──────────────┬──────────────────────────────┘
               ↓
[Validation Layer]
    → Email validation (97%+ accuracy)
    → Phone normalization (E.164 format)
    → Social URL deduplication
    ↓
[Update DataFrame at index with enriched fields]
    ↓
[Checkpoint every 500 records] ← save_checkpoint("enricher_partial")
    ↓
[Stage 7 Complete → Stage 8 CSV Output]
```

### State Management

```
[Checkpoint State Store] (pickle + parquet)
    ↓ (load on resume)
[Enricher] ←→ [done_indices set] → [Skip already processed]
    ↓
[HTTP Cache] ← RateLimitedSession reads before HTTP request
    ↓ (cache hit = instant return)
[Rate Limiter State] ← _last_request_time tracker
```

### Key Data Flows

1. **Kentucky Filtering Flow**: Stage 5 merge → Stage 6 dedup → **Stage 7 Kentucky filter** → enrichment loop → Stage 8 output. Filter applied at enrichment entry to minimize API costs.

2. **Waterfall Enrichment Flow**: Direct scrape attempt → IF missing email → API Provider 1 → IF fail → Provider 2 → ... → validation → update or skip.

3. **Cache-First Flow**: Request URL → SHA256 hash → check disk cache → cache hit? return JSON → cache miss? HTTP fetch → cache write → return.

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-10K orgs** | Current architecture sufficient. Single-threaded scraping with rate limiting (2 req/sec). BeautifulSoup + RateLimitedSession. Checkpoint every 500 records. |
| **10K-100K orgs** | Add request queue with async workers (aiohttp). Increase checkpoint frequency (every 100 records). Implement proxy rotation to distribute load across IPs. Consider upgrading to Playwright for JS-heavy sites only. |
| **100K+ orgs** | Migrate to distributed scraping (Kafka + Apache Flink). Deploy worker pool across multiple machines. Implement centralized cache (Redis). Use commercial proxy services (BrightData, ScraperAPI). Consider 3rd-party APIs as primary (Clearbit, ZoomInfo) with scraping as fallback. |

### Scaling Priorities

1. **First bottleneck**: Rate limiting causes 10-20 hour runtime for 80K orgs. **Fix**: Implement async HTTP with concurrent workers (10-50 concurrent requests with proxy rotation). Reduces runtime to 2-4 hours.

2. **Second bottleneck**: API costs accumulate ($0.01-0.10 per lookup). **Fix**: Optimize waterfall order (cheapest/fastest first). Cache API responses aggressively. Implement Kentucky-first filtering to reduce volume by 95%+.

3. **Third bottleneck**: Checkpoint overhead as dataset grows. **Fix**: Migrate from pickle to database checkpoints (SQLite or PostgreSQL). Store only deltas instead of full state snapshots.

## Anti-Patterns

### Anti-Pattern 1: Synchronous Scraping Without Queues

**What people do:** Call `http.get(url)` in a for-loop for 80K URLs with simple rate limiting sleep.

**Why it's wrong:** Serial execution creates 10-20 hour runtimes. Any single timeout (30 seconds) blocks the entire pipeline. Cannot distribute load across proxies/IPs effectively.

**Do this instead:** Implement async request queue with concurrent workers:

```python
# transformers/contact_discovery/async_scraper.py
async def scrape_batch(urls: list[str], concurrency: int = 20):
    queue = asyncio.Queue()
    for url in urls:
        await queue.put(url)

    workers = [scrape_worker(queue) for _ in range(concurrency)]
    await asyncio.gather(*workers)

async def scrape_worker(queue: asyncio.Queue):
    while not queue.empty():
        url = await queue.get()
        await async_http_client.get(url)  # aiohttp
        queue.task_done()
```

### Anti-Pattern 2: Scraping Before Filtering

**What people do:** Enrich all 80K orgs, then filter to Kentucky subset afterward.

**Why it's wrong:** Wastes 95% of API calls and scraping time on orgs outside target geography. Increases costs by 20x. Violates "do the least work" principle.

**Do this instead:** Filter to Kentucky subset BEFORE enrichment loop:

```python
# transformers/enricher.py
def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
    # FILTER FIRST - Kentucky orgs only
    ky_subset = df[df["state"].str.upper() == "KY"]
    self.logger.info(f"Kentucky subset: {len(ky_subset):,} orgs")

    needs_enrichment = ky_subset[
        ky_subset["website"].notna() &
        (ky_subset["email"].isna() | ky_subset["facebook_url"].isna())
    ].index

    # NOW enrich only Kentucky orgs
    for idx in needs_enrichment:
        # ... scraping logic ...
```

### Anti-Pattern 3: No Email Validation After Extraction

**What people do:** Extract emails via regex from HTML, store directly without validation.

**Why it's wrong:** Results in 20-40% invalid emails (personal accounts, disposable emails, format errors). Harms deliverability. Creates compliance issues (GDPR violations for scraped personal emails).

**Do this instead:** Validate all extracted emails through verification service:

```python
# transformers/api_integration/validators/email_validator.py
def validate_email(email: str, org_domain: str) -> bool:
    # Format validation
    if not EMAIL_PATTERN.match(email):
        return False

    # Skip generic/disposable
    if email in SKIP_EMAILS or is_disposable_domain(email):
        return False

    # Verify domain matches org website (reduces personal emails)
    email_domain = email.split("@")[1]
    if org_domain not in email_domain:
        logger.warning(f"Email domain mismatch: {email} vs {org_domain}")
        return False

    # Optional: API verification (Hunter.io, ZeroBounce)
    # return hunter_verify_api(email)  # 97%+ accuracy

    return True
```

### Anti-Pattern 4: Committing API Keys to Git

**What people do:** Store API keys directly in `config/settings.py` or hardcoded in scripts.

**Why it's wrong:** Exposes credentials in version control. Leads to API key theft, quota abuse, and security breaches. Violates SOC2 compliance requirements.

**Do this instead:** Use environment variables with .env file:

```python
# config/enrichment_settings.py
import os
from dotenv import load_dotenv

load_dotenv()

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

# .env (gitignored)
# HUNTER_API_KEY=abc123...
# CLEARBIT_API_KEY=def456...
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Hunter.io** | REST API (email verification) | $49/month for 1,000 searches; use for Kentucky subset only |
| **Clearbit** | REST API (company enrichment) | $99/month for 2,500 lookups; waterfall fallback after Hunter |
| **Apollo.io** | REST API (B2B contact data) | Free tier: 10,000 credits; use as tertiary fallback |
| **ZeroBounce** | REST API (email validation) | $16/1,000 validations; use post-scraping for all emails |
| **ProPublica** | REST API (existing - financials) | Free; already integrated in Stage 2 |
| **ScraperAPI** | Proxy service for web scraping | $49/month for 100K requests; use if IP bans occur |
| **Playwright** | Headless browser automation | Self-hosted; use only for JS-heavy sites (5-10% of cases) |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **Stage 7 ↔ utils/http_client** | Direct function calls | RateLimitedSession shared across enrichment components |
| **Enricher ↔ Contact Discovery** | Function calls with dataclass DTOs | EnrichmentResult(email, phone, social_urls) |
| **Waterfall ↔ API Providers** | Abstract BaseProvider interface | Each provider implements find_email(), find_phone() |
| **Enricher ↔ Checkpoint Manager** | File I/O via pickle | Saves (enrichments dict, done_indices set) |
| **Enricher ↔ Queue Manager** | asyncio.Queue (future) | Decouples producers (URL generators) from consumers (scrapers) |

## Build Order & Dependencies

### Suggested Implementation Phases

**Phase 1: Kentucky Filtering (Week 1)**
- Add state filter at Stage 7 entry: `df[df["state"] == "KY"]`
- Measure subset size (expected: ~3,000-4,000 orgs)
- Validate filter doesn't break existing pipeline
- **Why first**: Reduces scope by 95%; makes testing faster; minimizes API costs

**Phase 2: Enhanced Web Scraping (Week 1-2)**
- Extend `enricher.py` with phone number extraction (add PHONE_PATTERN regex)
- Improve social media patterns (YouTube, LinkedIn company pages)
- Add meta description extraction for mission statements (already exists)
- **Why second**: Maximizes free data before paid APIs; builds on existing scraper

**Phase 3: Email Validation Layer (Week 2)**
- Implement `validators/email_validator.py` with domain matching
- Integrate SKIP_EMAILS expansion (add .gov, .mil personal domains)
- Add optional API validation hook (ZeroBounce/Hunter)
- **Why third**: Ensures quality before moving to expensive API fallbacks

**Phase 4: Waterfall API Integration (Week 3)**
- Create `api_integration/waterfall.py` orchestrator
- Implement BaseProvider abstract class
- Add Hunter.io provider (primary for email)
- Add Clearbit provider (secondary for company data)
- **Why fourth**: Depends on validation layer; most complex component

**Phase 5: Async Queue System (Week 4 - Optional)**
- Refactor to async/await with aiohttp
- Implement worker pool pattern (10-20 concurrent)
- Add proxy rotation support (if needed)
- **Why last**: Optimization only needed if runtime >4 hours; not critical for MVP

### Component Dependencies

```
Phase 1: Kentucky Filter
    ↓ (enables focused testing)
Phase 2: Enhanced Web Scraping
    ↓ (provides data to validate)
Phase 3: Email Validation
    ↓ (required before API fallback)
Phase 4: Waterfall API
    ↓ (all enrichment complete)
Phase 5: Async Optimization (optional)
```

## Sources

### Architecture Patterns
- [ETL Frameworks in 2026 for Future-Proof Data Pipelines | Integrate.io](https://www.integrate.io/blog/etl-frameworks-in-2025-designing-robust-future-proof-data-pipelines/)
- [ETL Architecture and Design: Essential Steps and Patterns](https://www.matillion.com/blog/etl-architecture-design-patterns-modern-data-pipelines)
- [Best Practices to Engineering Big Data Pipeline Architecture](https://groupbwt.com/blog/big-data-pipeline-architecture/)
- [10 Common Data Integration Patterns: A Complete Guide for 2026](https://blog.skyvia.com/common-data-integration-patterns/)

### Data Enrichment & Contact Discovery
- [B2B Lead Generation with Web Scraping: The 2026 Playbook | Use Apify](https://use-apify.com/blog/lead-generation-web-scraping)
- [Zero to Production Scraping Pipeline: 2.5M Dataset in 22 Hours | ScrapeGraphAI](https://scrapegraphai.com/blog/zero-to-production-scraping-pipeline)
- [The 12 Best Data Enrichment Tools for Scalable Growth in 2026](https://www.limadata.com/blog-details/best-data-enrichment-tools)
- [A look at Web Data Scraping and Enrichment Pipeline | Medium](https://medium.com/@divyansh9144/a-look-at-web-data-scraping-and-enrichment-pipeline-2622de813750)

### Waterfall Enrichment & Failover
- [Waterfall Data Enrichment: Pros & Cons [2026]](https://www.cognism.com/blog/waterfall-enrichment)
- [Waterfall Enrichment: Ultimate Guide for 2026 - BetterContact](https://bettercontact.rocks/blog/waterfall-enrichment/)
- [What Is Waterfall Enrichment? | Medium](https://medium.com/@lloyd.rayner/what-is-waterfall-enrichment-06d96d58cb13)

### Rate Limiting & Scaling
- [What Is Rate Limiting & How to Avoid It](https://oxylabs.io/blog/rate-limiting)
- [Rate Limit in Web Scraping: How It Works & 5 Bypass Methods | Scrape.do](https://scrape.do/blog/web-scraping-rate-limit/)
- [Dealing with Rate Limiting Using Exponential Backoff](https://substack.thewebscraping.club/p/rate-limit-scraping-exponential-backoff)
- [How to Overcome Rate Limiting in Web Scraping](https://www.scrapehero.com/rate-limiting-in-web-scraping/)

### Web Scraping Technologies
- [Scrapy vs. Beautiful Soup: The 2026 Engineering Benchmark | HasData](https://hasdata.com/blog/scrapy-vs-beautifulsoup)
- [Crawlee vs. Scrapy vs. BeautifulSoup: The Ultimate Guide for 2026 | Use Apify](https://use-apify.com/blog/crawlee-vs-scrapy-vs-beautifulsoup-2026)
- [Web Scraping with Playwright [2026]](https://www.browserstack.com/guide/playwright-web-scraping)
- [Top 7 Python Headless Browsers in 2026 Compared | Scrape.do](https://scrape.do/blog/python-headless-browser/)

### Email Verification & Validation
- [15 Best Email Verification Tools in 2026 (With Real Benchmark Data)](https://hunter.io/email-verification-guide/best-email-verifiers/)
- [8 Waterfall Enrichment Tools: Maximize Contact Data Coverage in 2025 - Persana AI](https://persana.ai/blogs/waterfall-enrichment-tools)
- [11 Best Data Enrichment Tools to Use in 2026](https://skrapp.io/blog/data-enrichment-tools/)

### Social Media Scraping
- [The Ultimate Guide to the Best Social Media Scraping APIs in 2026 | SociaVault](https://sociavault.com/blog/best-social-media-scraping-apis-2026)
- [Social Media Scraping in 2026](https://scrapfly.io/blog/posts/social-media-scraping)
- [12 Best Social Media Scrapers for 2026: A Complete Guide | ProfileSpider](https://profilespider.com/blog/best-social-media-scrapers)

### Checkpoint & Resumability
- [Lost in the ETL Multiverse? Checkpoints Can Save You | Medium](https://thedataspartan.medium.com/lost-in-the-etl-multiverse-checkpoints-can-save-you-4d33d809f431)
- [Checkpoint-Based Recovery for Long-Running Data Transformations - Dev3lop](https://dev3lop.com/checkpoint-based-recovery-for-long-running-data-transformations/)
- [ETL 300: Incremental Processing Using Checkpoint Tables | Adobe Data Distiller](https://data-distiller.all-stuff-data.com/unit-3-data-distiller-etl-extract-transform-load/etl-300-incremental-processing-using-checkpoint-tables-in-data-distiller)

### Nonprofit Data Integration
- [U.S. Nonprofit Data APIs: Improving Transparency, Compliance, and Integration | Nordic APIs](https://nordicapis.com/u-s-nonprofit-data-apis-improving-transparency-compliance-and-integration/)
- [Architecture of Nonprofit data solutions in Microsoft Fabric - Microsoft for Nonprofits](https://learn.microsoft.com/en-us/industry/nonprofit/architecture-nonprofit-data-solutions)

### API Orchestration
- [Conducting Data: The Art of API Orchestration | Cyclr](https://cyclr.com/blog/conducting-data-the-art-of-api-orchestration)
- [APIs for AI Agents: The 5 Integration Patterns (2026 Guide) - Composio](https://composio.dev/blog/apis-ai-agents-integration-patterns)
- [How to Build an Enrichment API: Step-by-Step Guide [With Code Examples] - Persana AI](https://persana.ai/blogs/enrichment-api)

---
*Architecture research for: Nonprofit Data Enrichment / Veteran Org Directory*
*Researched: 2026-02-11*

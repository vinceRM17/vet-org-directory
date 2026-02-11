# Project Research Summary

**Project:** Veteran Organization Directory Data Enrichment
**Domain:** Nonprofit Data Enrichment / Contact Discovery
**Researched:** 2026-02-11
**Confidence:** HIGH

## Executive Summary

This project requires building a contact data enrichment pipeline for 80,784 US veteran/military support organizations. The recommended approach follows a multi-stage ETL pattern with waterfall enrichment (sequential failover across multiple data providers), checkpoint-based resumability for long-running jobs, and strict validation to ensure 95%+ data accuracy. The core challenge is balancing scraping scale (2-5K Kentucky orgs initially, 80K+ eventually) against API costs, rate limits, and data quality.

The research strongly recommends starting with Kentucky-first filtering (reduces scope by 95%), building robust validation infrastructure before scraping begins, and using a hybrid BeautifulSoup + Playwright approach that optimizes for speed while handling JavaScript-heavy nonprofit websites. Playwright 1.58.0, httpx 0.28.1, and Pandera 0.29.0 form the modern stack, replacing older tools (Selenium, requests, manual validation). Critical risk mitigation focuses on preventing silent data quality failures, memory exhaustion from browser context leaks, and rate limit cascading failures—all of which can corrupt data or cause multi-hour job failures.

The phased roadmap should prioritize infrastructure (validation, checkpointing, rate limiting) in Phase 1, direct web scraping in Phase 2, and defer expensive waterfall API integration to Phase 3 after validating that free scraping achieves acceptable match rates. This order maximizes learning while minimizing upfront API costs. Based on industry benchmarks, expect 40-60% email match rates from single-source scraping, increasing to 75-85% with waterfall enrichment.

## Key Findings

### Recommended Stack

Modern Python data enrichment stacks in 2026 center on async-first HTTP clients, headless browser automation for JavaScript rendering, and production-grade DataFrame validation. The research identifies critical upgrades from the existing stack: Playwright 1.58.0 (12% faster than Selenium with native async), httpx (replaces requests/aiohttp with HTTP/2 support), and Pandera for schema validation (prevents silent data corruption). Existing tools like RapidFuzz (fuzzy matching) and BeautifulSoup (HTML parsing) remain appropriate.

**Core technologies:**
- **Playwright 1.58.0**: Headless browser automation for JavaScript-heavy nonprofit sites — 12% faster page loads than Selenium, native async support, no WebDriver overhead
- **httpx 0.28.1**: Modern async HTTP client for APIs — replaces requests/aiohttp with HTTP/2, connection pooling, and requests-like ergonomic API
- **gql 4.0.0**: GraphQL client for Charity Navigator API — automatic batching, built-in validation, designed for GraphQL's cost-based rate limiting
- **Pandera 0.29.0**: DataFrame validation framework — type-safe schemas prevent silent data corruption, 3x faster than manual validation (requires Python 3.10+)
- **tenacity 9.0+**: Retry logic with exponential backoff and jitter — prevents rate limit cascading failures, battle-tested for API resilience
- **aiometer 0.5+**: Async rate limiting — precise control over concurrent requests and requests/second, essential for large-scale scraping

**Critical gap:** The current stack lacks retry logic, rate limiting, data validation, structured logging, and GraphQL client capabilities. Adding these is non-negotiable for production-grade enrichment.

**Version constraint:** Pandera 0.29.0 requires Python 3.10+. If upgrading from Python 3.9 is not feasible, alternative is using Pydantic for all validation (less ergonomic for DataFrames but compatible).

### Expected Features

Industry research reveals that nonprofit data enrichment has well-defined table stakes (users expect these or product feels incomplete) versus competitive differentiators (set products apart). Anti-features research highlights common pitfalls: enriching all fields always (wastes money), one-time enrichment without refresh (data decays 20-30% annually), and AI-generated contact guessing (low accuracy damages sender reputation).

**Must have (table stakes):**
- **Contact Data Append (Email/Phone/Website)** — core value proposition, users expect 95%+ accuracy
- **Address Validation** — USPS standardization is baseline for matching accuracy
- **Batch Processing** — CSV upload/export with async processing for 80K+ records
- **Basic Data Quality** — duplicate detection, deceased records, email verification before append
- **Match Rate Reporting** — dashboard showing enrichment success rate by field type
- **Do Not Call Flagging** — legal requirement for phone outreach, non-negotiable
- **Data Source Attribution** — transparency builds trust ("Phone from IRS, Email from website scrape")

**Should have (competitive differentiators):**
- **Waterfall Enrichment** — dramatically increases match rates (60% → 85%+) by trying multiple sources sequentially until verified match found
- **Kentucky-First Prioritization** — deep local data for KY orgs gives unique value for Active Heroes use case
- **Confidence Scoring** — show reliability of each enriched field (0-100%), let users decide threshold
- **Real-Time Enrichment** — API endpoint that enriches on insert, not just batch (add after MVP validation)
- **Automated Refresh** — re-enrich records quarterly to address 20-30% annual data decay

**Defer (v2+):**
- **Social Media Discovery** — high complexity (web scraping at scale, rate limiting, legal compliance), nice-to-have vs must-have
- **Mission Statement Extraction** — useful for categorization, not critical for contact enrichment
- **Multi-Source Verification** — premium feature (cross-reference 3+ sources before accepting), requires waterfall infrastructure first
- **Veteran-Specific Fields** — niche value, requires domain expertise to build correctly

**Cost implications:** Industry standard is $0.01-0.05 per data point enriched. For 80K records × 3 fields = 240K enrichments = $2,400-$12,000 in API costs. Kentucky filtering (2-5K orgs) reduces this to $120-$600 for initial validation.

### Architecture Approach

Data enrichment systems follow a three-layer architecture: orchestration (stage management, checkpointing, failover), enrichment (web scraping, API clients, contact extraction), and infrastructure (rate limiting, caching, queue management). The waterfall enrichment pattern is the industry gold standard for maximizing match rates: try Provider A, if fail → Provider B → Provider C until verified data found or all providers exhausted.

**Major components:**
1. **Checkpoint Manager** — saves pipeline state every 500 records using pickle; enables resume after crashes in 10-20 hour enrichment runs. Critical upgrade needed: atomic writes (write to temp file, then rename) to prevent corruption.
2. **Waterfall Enricher** — orchestrates sequential failover across multiple data providers (Hunter.io → Clearbit → Apollo for email). Stops at first verified match to minimize costs. Requires BaseProvider abstract class and per-provider implementations.
3. **Rate-Limited HTTP Client** — controls request frequency to avoid IP bans, implements exponential backoff with jitter on 429 errors, checks x-ratelimit-remaining header. Existing http_client.py needs enhancement: add jitter, Retry-After header support, and circuit breaker pattern.
4. **Hybrid Scraper (BeautifulSoup + Playwright)** — uses BeautifulSoup for static sites (90% of nonprofits, 10x faster), swaps to Playwright for JavaScript-heavy sites. Compositional approach optimizes speed vs capability.
5. **Validation Layer** — multi-layer validation prevents silent failures: schema validation (Pandera), format validation (regex for emails/phones), and anomaly detection (flag batches with >5% empty fields).

**Critical patterns:**
- **Kentucky filtering BEFORE enrichment loop** — reduces API costs by 95%, makes testing faster. Anti-pattern: enrich all 80K, then filter.
- **Batch processing with context lifecycle management** — close/recreate Playwright browser contexts every 50-100 URLs to prevent memory exhaustion (known issue: contexts accumulate 50-100MB RAM each).
- **Cache-first flow** — check disk cache before HTTP request (http_client.py already implements this), reduces redundant scraping on pipeline restarts.

### Critical Pitfalls

Research identified 7 critical pitfalls (project-killing if not addressed) plus 9 moderate and 4 minor pitfalls. The top risks cluster around data quality validation, memory management, and rate limiting—all preventable with proper infrastructure.

1. **Silent Data Quality Failures** — scrapers capture placeholder values ("Loading..."), CSS class names, or JavaScript error messages instead of actual contact info. Unlike crashes, these silently corrupt data for weeks. **Prevention:** Multi-layer validation (Pydantic schema + regex format + anomaly detection), expected-value baselines per website pattern, separate raw HTML storage for reprocessing.

2. **Memory Exhaustion from Browser Context Leaks** — Playwright issue #6319 shows contexts accumulate memory even after cleanup. At 2-5K orgs scale, crashes occur after 500-1000 sites. **Prevention:** Close/recreate browser contexts every 50-100 URLs, use asyncio instead of threads (30-40% less memory), implement checkpoint saving after each batch.

3. **Website Structure Change Detection Lag** — websites modify HTML structure without warning, selectors return empty results for weeks before detection. **Prevention:** Store raw HTML separately from parsed data (enables reprocessing), selector confidence scoring (flag extractions that return empty when historical success rate was >80%), daily test suites against key websites.

4. **Entity Resolution Complexity Underestimation** — orgs have wildly inconsistent naming ("Veterans of Foreign Wars Post 1234" vs "VFW Post 1234 - Louisville"). Simple EIN matching misses 40%+ duplicates. **Prevention:** Confidence scores for merges (EIN exact = 100%, fuzzy name = 70-85%), conservative thresholds initially (85% fuzzy match), audit log tracking merge decisions, manual review queue for edge cases.

5. **API Rate Limit Cascading Failures** — rate limit errors on one batch cause retry logic to trigger for all URLs, creating "thundering herd" that extends scraping from hours to days. **Prevention:** Exponential backoff WITH jitter (decorrelated jitter is 2026 best practice), respect Retry-After headers, circuit breaker pattern (after N consecutive failures, pause domain requests), per-domain rate limits.

6. **Checkpoint Data Corruption at Scale** — pickle files are not crash-safe; interrupted writes create corrupted state that forces full restart. **Prevention:** Atomic writes (write to temp, then rename), checkpoint versioning (keep last 3 checkpoints), add checksum validation, consider JSON Lines for large datasets.

7. **Contact Information Validation False Positives** — regex patterns capture invalid data: years (2024), decimal numbers (3.14), sample emails in privacy policies. **Prevention:** Layer validation (pattern → format → deliverability), exclude false positive patterns (consecutive same digits, years 2020-2030), context-aware extraction (prioritize "Contact Us" sections), confidence scoring per extraction context.

## Implications for Roadmap

Based on combined research, the roadmap should follow a build-validate-scale progression: infrastructure first (prevent pitfalls), direct scraping second (free data, learn patterns), API integration third (only after validating need and ROI). This order minimizes upfront costs while maximizing learning.

### Phase 1: Infrastructure & Kentucky Filtering
**Rationale:** Kentucky filtering reduces scope by 95% (80K → 2-5K orgs), making all subsequent phases faster and cheaper to test. Infrastructure (validation, checkpointing, rate limiting) must be bulletproof before scraping begins—fixing data corruption after the fact is impossible.

**Delivers:**
- Kentucky state filter at Stage 7 entry point
- Enhanced checkpoint system with atomic writes and versioning
- Pandera validation schemas for all DataFrames
- Upgraded http_client.py with jitter, Retry-After support, circuit breaker
- Memory-safe Playwright batch processing (context lifecycle management)

**Addresses features:**
- Basic Data Quality (table stakes)
- Match Rate Reporting infrastructure

**Avoids pitfalls:**
- Pitfall 1: Silent data quality failures (validation framework)
- Pitfall 2: Memory exhaustion (batch processing design)
- Pitfall 5: Rate limit cascading (jitter + circuit breaker)
- Pitfall 6: Checkpoint corruption (atomic writes)

**Research flag:** LOW — infrastructure patterns are well-documented, existing codebase provides foundation. Focus on implementation quality, not discovery.

---

### Phase 2: Direct Web Scraping & Validation
**Rationale:** Start with free data (direct website scraping) before spending on APIs. This validates scraping patterns, tunes extraction algorithms, and establishes baseline match rates for ROI comparison with paid APIs. Hybrid BeautifulSoup + Playwright approach optimizes for nonprofit website patterns (90% static, 10% JavaScript-heavy).

**Delivers:**
- Enhanced enricher.py with phone extraction, improved social media patterns
- Hybrid scraper (BeautifulSoup for static sites, Playwright for JS-heavy)
- Multi-layer contact validation (format + domain matching + context scoring)
- Robots.txt compliance checking
- Progress logging and monitoring dashboard

**Uses stack:**
- Playwright 1.58.0 (for JavaScript-heavy sites only, 5-10% of cases)
- BeautifulSoup 4.12+ (primary scraper for static sites)
- extract-emails 3.0+, phonenumbers 8.13+ (contact extraction)
- structlog 24.4+ (structured logging for debugging)

**Implements architecture:**
- Hybrid Scraper component
- Contact Discovery module (web_scraper.py, email_extractor.py, phone_extractor.py, social_finder.py)

**Addresses features:**
- Contact Data Append (table stakes) — email, phone, website
- Data Source Attribution (table stakes)

**Avoids pitfalls:**
- Pitfall 3: Website structure changes (multi-pattern selectors, monitoring)
- Pitfall 7: Contact validation false positives (multi-layer validation)
- Pitfall 10: Robots.txt violations (compliance checking)
- Pitfall 12: Playwright performance trade-offs (hybrid strategy)

**Research flag:** MEDIUM — web scraping patterns are well-documented, but nonprofit-specific extraction rules need iterative tuning based on Kentucky subset results. Plan for refinement cycles.

---

### Phase 3: API Integration & Waterfall Enrichment
**Rationale:** Only add paid APIs after measuring direct scraping match rates. If scraping achieves 40-60% email coverage (industry baseline), waterfall enrichment can boost to 75-85%. Charity Navigator GraphQL and VA Facilities REST provide nonprofit-specific enrichment. This phase requires careful cost management: query cost calculation for GraphQL, per-provider ROI tracking.

**Delivers:**
- Charity Navigator GraphQL integration (financials, ratings)
- VA Facilities API integration (veteran org verification)
- Waterfall enrichment orchestrator (Hunter.io → Clearbit → Apollo failover)
- Query cost calculator for GraphQL cost-based rate limiting
- Per-provider success rate and cost tracking

**Uses stack:**
- gql 4.0.0 (GraphQL client for Charity Navigator)
- httpx 0.28.1 (async HTTP for VA Facilities, waterfall providers)
- tenacity 9.0+ (retry logic with exponential backoff)
- aiometer 0.5+ (rate limiting for concurrent API calls)

**Implements architecture:**
- Waterfall Enricher component
- API Integration module (waterfall.py, providers/*, validators/*)

**Addresses features:**
- Waterfall Enrichment (differentiator) — 85-95% match rates vs 60% single-source
- Confidence Scoring (differentiator) — multi-source verification enables scoring

**Avoids pitfalls:**
- Pitfall 4: Entity resolution complexity (multi-source confidence scoring, merge audit)
- Pitfall 9: Charity Navigator GraphQL cost miscalculation (query cost calculator)

**Research flag:** MEDIUM — waterfall pattern is well-documented, but per-provider API integration needs research. Plan for `/gsd:research-phase` on Charity Navigator GraphQL specifics (cost structure, query optimization) and Hunter.io/Clearbit/Apollo API capabilities.

---

### Phase 4: Quality Assurance & Production Readiness
**Rationale:** After enrichment pipeline is functional, focus shifts to production quality: manual review for edge cases, automated monitoring for website structure changes, incremental update strategy for data freshness. This phase addresses long-term maintainability and data decay.

**Delivers:**
- Manual review interface for low-confidence matches (<85%)
- Automated monitoring with daily validation runs against key websites
- Enrichment history tracking (audit trail per field)
- Incremental update strategy with priority scoring (stale data, incomplete records)
- Do Not Call registry integration

**Addresses features:**
- Manual Review Interface (table stakes)
- Enrichment History (differentiator)
- Automated Refresh (differentiator) — addresses 20-30% annual data decay
- Do Not Call Flagging (table stakes) — legal compliance

**Avoids pitfalls:**
- Pitfall 8: Incremental update strategy missing (timestamp tracking, priority scoring)

**Research flag:** LOW — manual review and monitoring patterns are standard. Focus on implementation.

---

### Phase 5: Scale & Optimization (Post-MVP)
**Rationale:** After validating on Kentucky subset (2-5K orgs), scale to full 80K+ dataset. This phase requires performance optimization: async queue system with concurrent workers, proxy rotation for rate limit distribution, potential migration from pickle to database checkpoints.

**Delivers:**
- Async queue system with 10-20 concurrent workers (asyncio + aiohttp)
- Proxy rotation support (if IP bans occur)
- Database-backed checkpoints (SQLite or PostgreSQL) replacing pickle
- Real-Time Enrichment API (enrich on insert, not just batch)

**Addresses features:**
- Real-Time Enrichment (differentiator) — API endpoint for new org additions
- Batch Processing optimization for 80K+ scale

**Avoids pitfalls:**
- Performance traps identified in PITFALLS.md (synchronous scraping, no async)

**Research flag:** MEDIUM — async scraping patterns are well-documented, but scaling to 80K+ may reveal nonprofit-specific bottlenecks. Monitor runtime and adjust concurrency.

---

### Phase Ordering Rationale

**Dependency-driven order:**
- Infrastructure (Phase 1) must precede scraping (Phase 2) — validation/checkpointing prevents data corruption
- Direct scraping (Phase 2) should precede API integration (Phase 3) — establishes baseline for ROI comparison
- API integration (Phase 3) must precede quality assurance (Phase 4) — manual review needs complete data
- Scale (Phase 5) comes last — optimize only after validating patterns on smaller subset

**Risk mitigation order:**
- Address critical pitfalls (1, 2, 5, 6) in Phase 1 before collecting data
- Address data quality pitfalls (3, 7) in Phase 2 during scraping implementation
- Address integration complexity pitfalls (4, 9) in Phase 3 when adding multi-source enrichment

**Cost optimization order:**
- Start with free data (web scraping) before paid APIs
- Validate need for waterfall enrichment by measuring single-source match rates
- Kentucky filtering (95% scope reduction) makes Phases 1-4 cheaper to test

**Architecture pattern alignment:**
- Phase 1 builds Infrastructure Layer (rate limiting, caching, checkpointing)
- Phase 2 builds Enrichment Layer (web scraping, contact extraction)
- Phase 3 builds Orchestration Layer (waterfall failover, multi-API coordination)

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (API Integration):** Charity Navigator GraphQL cost structure and query optimization needs specific research. Hunter.io/Clearbit/Apollo API capabilities, rate limits, and pricing need validation. Recommend `/gsd:research-phase` before Phase 3 planning.
- **Phase 5 (Scale):** Scaling to 80K+ may reveal nonprofit-specific bottlenecks (many orgs on shared hosting with aggressive rate limiting). Monitor runtime on full dataset and adjust strategy.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Infrastructure):** Checkpoint, validation, and rate limiting patterns are well-documented. Existing codebase provides foundation.
- **Phase 2 (Scraping):** BeautifulSoup + Playwright hybrid is established pattern. Focus on iterative tuning, not discovery.
- **Phase 4 (Quality Assurance):** Manual review and monitoring patterns are standard across data enrichment systems.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All recommended technologies verified via PyPI (versions current as of Jan 2026), official documentation, and 2025/2026 community sources. Playwright, httpx, Pandera are production-proven. |
| Features | MEDIUM | Feature categories (table stakes, differentiators, anti-features) validated against 5 competitor products and industry benchmarks. Waterfall enrichment and confidence scoring patterns confirmed across multiple sources. Cost estimates ($2.4K-$12K for 80K records) align with industry pricing ($0.01-0.05/field). Confidence is MEDIUM vs HIGH because nonprofit-specific feature priorities may differ from general B2B data enrichment. |
| Architecture | HIGH | Three-layer architecture (orchestration, enrichment, infrastructure) is standard across data enrichment systems. Waterfall failover pattern documented in BetterContact, Apollo, and Cognism sources. Checkpoint-based resumability and rate limiting patterns verified across ETL framework documentation. |
| Pitfalls | HIGH | Critical pitfalls (silent data quality failures, memory exhaustion, rate limiting) confirmed via multiple sources: Playwright GitHub issues, web scraping monitoring articles, API rate limit best practices. Entity resolution complexity validated against nonprofit-specific CRM data management sources. Recovery strategies informed by production data pipeline documentation. |

**Overall confidence:** HIGH

The research draws from official documentation (Playwright, httpx, Pandera, gql), established industry sources (ScrapingBee, BetterContact, Cognism), and nonprofit-specific data management literature. Stack recommendations are based on verified 2026 versions and performance benchmarks. Architecture patterns align with existing codebase structure (http_client.py, checkpoint.py, enricher.py already implement recommended patterns). Pitfalls are substantiated by specific issue numbers (Playwright #6319) and community consensus.

### Gaps to Address

**API-specific details need validation during implementation:**
- **Charity Navigator GraphQL query cost structure** — documentation exists but specific cost per field needs testing to optimize query batching. Plan for initial test queries to measure actual costs.
- **Hunter.io/Clearbit/Apollo rate limits and pricing** — free tier limits need confirmation before waterfall integration. Budget for potential paid tiers if free limits insufficient for Kentucky subset.

**Nonprofit-specific extraction patterns need iterative tuning:**
- **Contact extraction rules for veteran organizations** — research provides general patterns, but veteran org websites may have specific quirks (military jargon in contact forms, VSO post numbering in URLs). Plan for refinement based on Kentucky subset results.
- **Entity resolution for parent/chapter relationships** — "Veterans of Foreign Wars" parent org vs "VFW Post 1234" chapters need custom deduplication rules. Research identifies pattern but implementation needs domain expertise.

**Scale-specific bottlenecks unknown until testing:**
- **Playwright memory usage at 2-5K scale** — research identifies context leak issue and mitigation (batch processing), but actual memory profile on nonprofit sites needs measurement. Monitor RAM usage during Kentucky subset scraping.
- **Rate limit thresholds for nonprofit websites** — many small nonprofits use shared hosting with aggressive rate limiting. Research recommends 2 req/sec conservative start, but actual limits vary. Plan for per-domain rate limit tuning.

**Legal compliance details need review:**
- **Do Not Call registry access fees** — research identifies 2026 fee structure ($82/area code, max $22,626 nationwide), but nonprofit exemptions may apply. Consult legal before implementation.
- **GDPR applicability for US nonprofit data** — research identifies GDPR requirements if any EU contacts exist, but Active Heroes' Kentucky focus likely limits exposure. Verify data scope during planning.

**Incremental update strategy needs design:**
- **Optimal refresh frequency** — research identifies 20-30% annual data decay, suggesting quarterly refresh, but optimal frequency depends on Active Heroes' use case. Design priority scoring system based on user needs.
- **Change detection for websites** — research recommends ETags and Last-Modified headers, but many nonprofit sites don't implement these. Design fallback strategy (content hash comparison, periodic full re-scrape).

## Sources

### Primary (HIGH confidence)

**Technology Stack:**
- Playwright Python PyPI (https://pypi.org/project/playwright/) — Version 1.58.0, Jan 2026
- httpx PyPI (https://pypi.org/project/httpx/) — Version 0.28.1, official documentation
- Pandera PyPI (https://pypi.org/project/pandera/) — Version 0.29.0, Jan 2026
- gql GitHub (https://github.com/graphql-python/gql) — Official repository and documentation
- Charity Navigator GraphQL API (https://www.charitynavigator.org/products-and-services/graphql-api/) — Official documentation
- VA Lighthouse APIs (https://developer.va.gov/) — Official developer portal

**Architecture Patterns:**
- Waterfall Enrichment: Ultimate Guide for 2026 - BetterContact (https://bettercontact.rocks/blog/waterfall-enrichment/)
- Zero to Production Scraping Pipeline: 2.5M Dataset in 22 Hours | ScrapeGraphAI (https://scrapegraphai.com/blog/zero-to-production-scraping-pipeline)
- ETL Frameworks in 2026 for Future-Proof Data Pipelines | Integrate.io (https://www.integrate.io/blog/etl-frameworks-in-2025-designing-robust-future-proof-data-pipelines/)

**Pitfalls:**
- Playwright Memory Issues - GitHub #6319 (https://github.com/microsoft/playwright/issues/6319)
- How to Fix Inaccurate Web Scraping Data: 2026 Best Practices (https://brightdata.com/blog/web-data/fix-inaccurate-web-scraping-data)
- Dealing with Rate Limiting Using Exponential Backoff (https://substack.thewebscraping.club/p/rate-limit-scraping-exponential-backoff)

### Secondary (MEDIUM confidence)

**Feature Research:**
- Data Enrichment for Nonprofits — NXUnite (https://nxunite.com/data-enrichment-for-nonprofits/)
- Best 15 Contact Data Enrichment Tools for Sales Teams in 2026 (https://generect.com/blog/contact-data-enrichment/)
- 22 Best Data Enrichment Tools for B2B Sales in 2026 (https://www.bookyourdata.com/blog/data-enrichment-tools)
- Waterfall Enrichment: Pros & Cons [2026] (https://www.cognism.com/blog/waterfall-enrichment)

**Legal and Compliance:**
- Q&A for Telemarketers & Sellers About DNC Provisions in TSR | FTC (https://www.ftc.gov/business-guidance/resources/qa-telemarketers-sellers-about-dnc-provisions-tsr-0)
- Telemarketer Fees to Access FTC's National Do Not Call Registry to Increase in 2026 | FTC (https://www.ftc.gov/news-events/news/press-releases/2025/08/telemarketer-fees-access-ftcs-national-do-not-call-registry-increase-2026)
- A Nonprofit's Guide to Navigating Data Privacy Laws - Deep Sync (https://deepsync.com/nonprofit-data-privacy/)

**Nonprofit-Specific:**
- Solving Nonprofit Industry CRM Data Management Challenges (https://blog.insycle.com/nonprofit-data-management)
- Common Data Model for Nonprofits (https://learn.microsoft.com/en-us/industry/nonprofit/common-data-model-for-nonprofits)

### Tertiary (LOW confidence)

**Contact Extraction:**
- extract-emails PyPI (https://pypi.org/project/extract-emails/) — June 2025 release, needs validation in production
- Contact Details Scraper API (https://apify.com/practicaltools/contact-details-scraper/api/python) — Alternative approach, not yet tested

**Social Media Scraping:**
- GitHub - Nonprofit-Open-Data-Collective/webscraper (https://github.com/Nonprofit-Open-Data-Collective/webscraper) — Community project, unknown maintenance status
- The Ultimate Guide to the Best Social Media Scraping APIs in 2026 | SociaVault (https://sociavault.com/blog/best-social-media-scraping-apis-2026) — Commercial source, needs validation

---

*Research completed: 2026-02-11*
*Ready for roadmap: yes*
*Next step: Requirements definition (gsd-requirements-writer)*

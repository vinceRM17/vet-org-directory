# Pitfalls Research

**Domain:** Nonprofit Data Enrichment with Web Scraping and API Integration
**Researched:** 2026-02-11
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Silent Data Quality Failures

**What goes wrong:**
Scrapers capture placeholder values, loading spinners, or JavaScript error messages instead of actual contact information. Unlike obvious crashes, these silent failures corrupt data for weeks before detection. Examples: "Loading..." instead of email addresses, "null" strings instead of phone numbers, or CSS class names accidentally extracted as contact info.

**Why it happens:**
JavaScript-heavy websites load content asynchronously after the initial HTML response. Traditional HTTP scrapers (BeautifulSoup) receive incomplete page structures when content loads milliseconds or seconds after page load through AJAX calls. Even with Playwright, timing issues occur if wait conditions are not properly configured for each site's specific loading patterns.

**How to avoid:**
- Implement multi-layer validation: schema validation (Pydantic), format validation (regex for emails/phones), and anomaly detection (flag batches with >5% empty fields)
- Create expected-value baselines per website pattern (e.g., if scraping 100 veteran org sites, 80%+ should have at least one contact method)
- Add checksum validation to detect when websites modify structure or formatting
- Separate storage into raw HTML and parsed data layers so you can reprocess without re-downloading if parsing logic changes
- Use Playwright's explicit wait conditions for each contact info element type, not just generic page load

**Warning signs:**
- Sudden drop in data completeness rates (e.g., email field went from 60% filled to 15% filled)
- String values that shouldn't appear in contact fields ("undefined", "Loading", "{email}")
- Unusual character counts (emails suddenly averaging 3 characters instead of 20)
- Batch processing shows consistent gaps at specific record ranges (indicates a specific site changed)

**Phase to address:**
Phase 1 (Infrastructure) — validation framework must be in place before scraping begins. Phase 2 (Scraping Implementation) — per-site validation rules and monitoring dashboards.

---

### Pitfall 2: Memory Exhaustion from Browser Context Leaks

**What goes wrong:**
When scraping thousands of websites with Playwright, memory consumption grows exponentially rather than staying flat. A known Playwright issue (GitHub #6319) shows memory increases when the same browser context is reused across pages. At scale (2-5K organizations), this causes the scraper to crash after processing 500-1000 sites, losing all progress since the last checkpoint.

**Why it happens:**
Playwright browser contexts accumulate memory for each page navigation even after explicit cleanup. Each context uses 50-100MB RAM, and thread-based approaches use more memory than async approaches. Without proper context lifecycle management, memory usage spirals from hundreds of MB to multiple GB.

**How to avoid:**
- Close and recreate browser contexts every 50-100 URLs (batch processing pattern)
- Use asyncio instead of threads (30-40% less memory for same concurrency)
- Limit concurrent browser contexts to match available RAM (6GB RAM = ~50-thread concurrency max)
- Implement checkpoint saving after each batch so crashes don't lose progress
- Monitor memory usage per batch and auto-restart if threshold exceeded
- For Kentucky subset (2-5K orgs), process in chunks of 100 URLs max

**Warning signs:**
- Memory usage climbing steadily throughout run (should be sawtooth pattern with batching)
- Crashes occurring at predictable intervals (every N sites processed)
- System swap usage increasing during scraping runs
- Playwright timeout errors increasing as run progresses (sign of resource exhaustion)

**Phase to address:**
Phase 1 (Infrastructure) — design batch processing and checkpoint architecture. Phase 2 (Scraping Implementation) — implement memory-safe context lifecycle management.

---

### Pitfall 3: Website Structure Change Detection Lag

**What goes wrong:**
Websites modify their HTML structure without warning. CSS selectors that worked for months return empty results when developers change class names or restructure layouts. The scraper continues running successfully (no errors thrown) but extracts zero or incorrect data for weeks before anyone notices. If a site changes from `<div class="price">` to `<div class="current-price">`, the scraper might accidentally grab nearby text (like a timestamp) that happens to be in a similar DOM location.

**Why it happens:**
Websites continuously improve without maintaining backward compatibility for automated tools. Organizations redesign sites, change CMS templates, or deploy A/B tests that alter page structure. Without active monitoring, selectors break silently because BeautifulSoup/Playwright return empty results rather than throwing exceptions.

**How to avoid:**
- Store raw HTML separately from parsed data (enables reprocessing after fixing selectors)
- Implement selector confidence scoring: flag extractions that return empty when historical success rate was >80%
- Create test suites with snapshots of key websites; re-run daily to detect breakage
- Version your selectors per website and track last-successful extraction date
- Use multiple selector strategies per field (e.g., try ID first, then class, then xpath)
- Set up alerts when extraction success rate drops >20% for any data source
- Build fallback extraction patterns (if primary email pattern fails, try secondary patterns)

**Warning signs:**
- Extraction success rates declining for specific domains over time
- Sudden increase in records with empty fields from previously reliable sources
- Batch reports showing complete data for old records, empty data for new records from same source
- User reports that data for known-good organizations is missing

**Phase to address:**
Phase 2 (Scraping Implementation) — build multi-pattern selectors and success tracking. Phase 3 (Monitoring) — automated alerts and daily validation runs.

---

### Pitfall 4: Entity Resolution Complexity Underestimation

**What goes wrong:**
Organizations have wildly inconsistent naming across data sources: "Veterans of Foreign Wars Post 1234" vs "VFW Post 1234 - Louisville" vs "V.F.W. POST 1234". Simple EIN matching misses 40%+ of duplicates because many nonprofits don't have EINs in all sources. Fuzzy name matching generates false positives when two different organizations have similar names in the same city. URL domain matching fails when orgs use multiple domains or change domains. The result: either massive duplicate records (poor user experience) or over-aggressive deduplication (lost data).

**Why it happens:**
Nonprofit data lacks unique identifiers across sources. The project has 3-tier deduplication (EIN exact, fuzzy name+city, URL domain) but this covers only the most obvious cases. Real-world issues include: chapters vs parent orgs, address variations ("123 Main St" vs "123 Main Street"), name abbreviations, merged organizations, and temporary vs permanent URLs. With 80K+ orgs and multiple enrichment sources, the combinatorial complexity explodes.

**How to avoid:**
- Track deduplication decisions in audit log (which records were merged, why, with what confidence)
- Implement confidence scores for merges: EIN exact = 100%, fuzzy name = 70-85%, URL domain = 60%
- Use conservative thresholds initially (85% fuzzy match) and gradually increase only with validation
- Preserve pre-dedup data separately so over-aggressive merges can be reversed
- Add manual review queue for edge cases: same domain but different cities, similar names with low confidence
- Consider ML-based entity resolution for scale (but not for MVP)
- For veteran orgs specifically: handle "Post ###" patterns, parent/chapter relationships, VSO acronyms

**Warning signs:**
- Deduplication stats show too many merges (>30% of records merged) or too few (<5% merged)
- User feedback about "missing" organizations that were over-merged
- Records with data_sources concatenating >5 sources (likely over-merged)
- Organizations in the output with conflicting addresses or states

**Phase to address:**
Phase 1 (Infrastructure) — design merge confidence scoring system. Phase 2 (Integration) — implement per-source deduplication rules. Phase 4 (Quality Assurance) — manual review queue and merge audit reports.

---

### Pitfall 5: API Rate Limit Cascading Failures

**What goes wrong:**
When scraping 2-5K org websites, rate limit errors (HTTP 429) on one batch cause the retry logic to trigger for all URLs in that batch. Without proper exponential backoff with jitter, multiple scrapers retry simultaneously, creating a "thundering herd" that keeps triggering rate limits. This extends scraping time from hours to days and can result in IP bans. For API integrations (Charity Navigator GraphQL, VA Facilities REST), hitting rate limits without respecting Retry-After headers leads to account suspension.

**Why it happens:**
The http_client.py has basic retry logic with exponential backoff, but doesn't implement jitter (randomness in wait times) or distributed retry patterns. When processing in batches of 100 URLs, a single rate limit can cascade to the entire batch retrying at similar intervals. GraphQL APIs like Charity Navigator have different rate limit structures than REST APIs (cost-based per query vs request-count-based), requiring different handling strategies.

**How to avoid:**
- Implement exponential backoff WITH jitter (decorrelated jitter is 2026 best practice)
- Always respect Retry-After headers before retrying
- Check x-ratelimit-remaining header; if 0, wait until x-ratelimit-reset time
- Use circuit breaker pattern: after N consecutive failures from a domain, pause all requests to that domain for configured time
- For GraphQL APIs: calculate query cost upfront and batch queries under cost limits
- Store failed URLs in separate queue for retry with different strategies (different proxy, longer timeout, alternative scraper)
- Log rate limit patterns to identify problematic domains and adjust per-domain rate limits
- For Kentucky subset: start with conservative 2 req/sec, adjust based on observed limits

**Warning signs:**
- Logs showing repeating 429 errors in tight clusters
- Total scraping time far exceeding estimates (should be ~10-20 hours for 2-5K sites, not days)
- Multiple retries all failing at similar timestamps (indicates no jitter)
- API providers sending warning emails about rate limit violations

**Phase to address:**
Phase 1 (Infrastructure) — enhance http_client.py with jitter, circuit breaker, and Retry-After handling. Phase 2 (Scraping Implementation) — per-domain rate limits and monitoring.

---

### Pitfall 6: Checkpoint Data Corruption at Scale

**What goes wrong:**
The checkpoint.py uses pickle for save/resume functionality. When scraping crashes mid-batch (due to memory issues, rate limits, or network failures), the checkpoint file can become corrupted (EOFError, UnpicklingError). The pipeline then ignores the corrupted checkpoint and restarts from scratch, losing hours of scraping progress. For large datasets (5K+ orgs), this creates a loop where crashes happen before completion and restarts never finish.

**Why it happens:**
Pickle files are not crash-safe; a write interrupted mid-operation creates corrupted state. The current error handling returns None on load failure, which triggers a full restart. With long-running scraping jobs (10-20 hours), the probability of at least one crash approaches 100%. Network failures, memory exhaustion, and OS interruptions all cause incomplete checkpoint writes.

**How to avoid:**
- Use atomic writes: write to temp file, then rename (filesystem guarantees atomicity)
- Implement checkpoint versioning: keep last 3 checkpoints, not just current
- Add checkpoint validation: store checksum with data, verify on load
- Consider JSON Lines instead of pickle for large datasets (more crash-resistant, easier to debug)
- Checkpoint more frequently but with incremental strategy: save delta since last checkpoint
- Separate storage: failed URLs queue, completed URLs set, enrichment data cache
- For web scraping specifically: checkpoint after every batch of 50-100 URLs, not per-URL
- Implement emergency recovery: extract partial data from corrupted checkpoints rather than discarding

**Warning signs:**
- Logs showing "Failed to load checkpoint" warnings
- Scraping restarts from beginning multiple times
- Checkpoint files with odd sizes (not matching typical data sizes)
- Inconsistent checkpoint timestamps (should be regular intervals)

**Phase to address:**
Phase 1 (Infrastructure) — redesign checkpoint system with atomic writes and versioning before starting large-scale scraping.

---

### Pitfall 7: Contact Information Validation False Positives

**What goes wrong:**
Regex patterns designed to extract emails and phone numbers capture invalid data: years (2024), decimal numbers (3.14), random number sequences, email-like strings that aren't emails ("[email protected]"), or phone numbers from embedded scripts. Without strict validation, the directory fills with junk contact data that damages credibility and wastes enrichment API calls trying to verify invalid contacts.

**Why it happens:**
Aggressive regex patterns prioritize recall over precision to avoid missing valid contacts. Websites contain phone-number-shaped and email-shaped text that isn't contact info: copyright years, monetary values, sample emails in privacy policies, phone numbers in marketing copy, or obfuscated emails to prevent spam bots. The tension between catching all real contacts vs avoiding false positives requires iterative tuning.

**How to avoid:**
- Layer validation: pattern recognition (regex) → format validation → deliverability checks
- Exclude common false positive patterns: consecutive same digits (1111111111), years (2020-2030), small numbers (<1000000)
- Use context-aware extraction: prioritize contacts near "Contact Us" headings or in footer/header sections
- Implement confidence scoring: phone in footer with "Call us" text = high confidence, phone in blog post body = low confidence
- For emails specifically: validate TLD against known list, check for disposable email domains, skip example.com/test.com
- For phones specifically: validate against North American Numbering Plan format, exclude extension-only numbers
- Test extraction patterns against known-good and known-bad examples before production
- Consider using specialized contact extraction services for validation (AtData, IPQS) on sampled subset

**Warning signs:**
- Extracted phone numbers with unusual digit patterns (all zeros, repeating sequences)
- Email addresses with invalid TLDs or obvious fake patterns
- Contact info counts that seem too high (if 95% of sites have 5+ emails, something's wrong)
- User complaints about incorrect contact information

**Phase to address:**
Phase 2 (Scraping Implementation) — implement multi-layer validation for contact extraction. Phase 3 (Quality Assurance) — sample validation against manual review.

---

## Moderate Pitfalls

### Pitfall 8: Incremental Update Strategy Missing

**What goes wrong:**
After initial scraping of 2-5K organizations, updating the data requires re-scraping everything. For 80K+ orgs in the full dataset, full refresh takes days and wastes compute on unchanged data. Without incremental update strategy, data becomes stale quickly because full refreshes are too expensive to run frequently.

**Prevention:**
- Design for incremental updates from the start: track last-scrape timestamp per organization
- Prioritize updates based on: data completeness (scrape incomplete records more often), data age (refresh >90 day old data), and source reliability (unreliable sources need more frequent checks)
- Implement Change Data Capture (CDC) for API sources that support it
- Use hybrid strategy: full refresh quarterly, incremental updates weekly
- For web scraping: store ETags or Last-Modified headers to detect changes before scraping
- Consider crawl budget: allocate more frequent scraping to high-value orgs (large budgets, many programs)

**Phase to address:**
Phase 1 (Infrastructure) — design timestamp tracking and priority scoring system.

---

### Pitfall 9: Charity Navigator GraphQL Cost Miscalculation

**What goes wrong:**
Unlike REST APIs with per-request rate limits, GraphQL APIs like Charity Navigator use cost-based limits where each field in a query has a computational cost measured in "points". A complex query requesting many nested fields can consume an entire rate limit in a single request. Without upfront cost calculation, the scraper burns through quota on inefficient queries.

**Prevention:**
- Read Charity Navigator API documentation for cost structure per field
- Calculate total query cost before execution; split high-cost queries into multiple cheaper queries
- Use GraphQL query fragments to reuse efficient patterns
- Request only needed fields; avoid nested relationships unless required
- Monitor remaining quota via response headers (x-ratelimit-remaining)
- Implement query cost budgeting: if cost > threshold, defer or split query
- For 80K EIN lookups: batch queries efficiently under cost limits rather than one-per-request

**Phase to address:**
Phase 2 (API Integration) — implement query cost calculator and batching strategy for Charity Navigator.

---

### Pitfall 10: Robots.txt Compliance Violations

**What goes wrong:**
While robots.txt is not legally binding in most jurisdictions, ignoring it creates legal and reputational risk. In 2026, courts use robots.txt compliance as evidence of good faith, and violations can support "technical harm" claims. For a nonprofit project serving Active Heroes, being flagged for aggressive scraping damages relationships with organizations you're trying to catalog.

**Prevention:**
- Check and respect robots.txt for every domain before scraping
- Obey Crawl-delay directives (many nonprofits have limited hosting and need throttling)
- Use identifiable User-Agent string (already in http_client.py as "VetOrgDirectory/1.0")
- Avoid collecting PII beyond publicly displayed contact info
- Document compliance procedures for transparency
- For organizations that disallow scraping: contact them directly to request data or skip them
- Note: Robots.txt compliance carries more weight in legal proceedings as of 2026

**Phase to address:**
Phase 2 (Scraping Implementation) — add robots.txt parser before website scraping begins.

---

### Pitfall 11: Data Schema Inconsistency Across Sources

**What goes wrong:**
IRS BMF uses full state names ("Kentucky"), VA Facilities uses state codes ("KY"), Charity Navigator uses abbreviations in some fields but full names in others. Address formats vary wildly: "123 Main St" vs "123 Main Street Apt 5" vs "PO Box 123". Phone numbers come as (555)123-4567, 555-123-4567, 5551234567, or +1.555.123.4567. Without normalization, deduplication fails and data quality suffers.

**Prevention:**
- The normalizer.py already exists but may need enhancement for new sources
- Create canonical format definitions: state = 2-letter uppercase, phone = E.164 format, URL = lowercase without www
- Normalize immediately after extraction, before storage
- Use usaddress library for address parsing (already in dependencies)
- Build validation tests comparing normalized outputs to expected formats
- Track normalization failures (fields that couldn't be normalized) for manual review

**Phase to address:**
Phase 2 (Integration) — enhance normalizer.py for new data sources and contact info formats.

---

### Pitfall 12: Playwright vs BeautifulSoup Performance Trade-offs

**What goes wrong:**
Blindly using Playwright for all scraping wastes time and resources. Playwright is 6GB RAM for 50-thread concurrency and slower than BeautifulSoup for static content. Using BeautifulSoup on JavaScript-heavy sites returns incomplete data. The wrong tool for each site type creates either performance problems or data quality problems.

**Prevention:**
- Profile sample sites first: check if content loads without JavaScript (View Source shows data → BeautifulSoup)
- Use Playwright only for sites requiring JavaScript rendering (contact info loaded via AJAX)
- For Kentucky subset testing: categorize sites as static vs dynamic before bulk scraping
- Hybrid approach: try BeautifulSoup first, fall back to Playwright if extraction fails validation
- Consider pre-screening: check site technology stack (Wix, Squarespace, custom CMS) to predict rendering needs
- Benchmark both approaches on sample of 50 sites to optimize strategy

**Phase to address:**
Phase 2 (Scraping Implementation) — implement hybrid extraction strategy with fallback logic.

---

## Minor Pitfalls

### Pitfall 13: VA Facilities API Key Not Configured

**What goes wrong:**
The va_facilities.py extractor is written but needs free API key in .env as VA_FACILITIES_API_KEY. Without this, Stage 4 of the pipeline fails silently or skips VA facilities data.

**Prevention:**
- Obtain free API key from developer.va.gov
- Add to .env file before running pipeline
- Update CLAUDE.md documentation with API key setup instructions
- Add validation: check for required API keys before starting pipeline stages that need them

**Phase to address:**
Phase 1 (Setup) — obtain and configure API keys before pipeline execution.

---

### Pitfall 14: NODC Extractor URLs Outdated

**What goes wrong:**
The nodc.py extractor targets Nonprofit Open Data Collective GitHub CSV URLs that have changed. The extractor fails and skips this data source.

**Prevention:**
- Research current NODC data locations (check nonprofitdata.com or GitHub repo)
- Update URLs in nodc.py or deprecate extractor if source no longer available
- Add URL validation tests to detect when source URLs change
- Document alternative sources for same data if NODC is unavailable

**Phase to address:**
Phase 1 (Setup) — fix or deprecate NODC extractor before data collection begins.

---

### Pitfall 15: Social Media URL Format Variations

**What goes wrong:**
Facebook URLs appear as facebook.com/page, fb.com/page, m.facebook.com/page, facebook.com/pages/Name/ID. Twitter/X URLs as twitter.com/handle, x.com/handle. LinkedIn as linkedin.com/company/name vs linkedin.com/in/person. Without normalization, deduplication fails to recognize identical accounts.

**Prevention:**
- Create canonical format per platform: facebook.com/username, twitter.com/handle (or decide on x.com standard)
- Strip mobile prefixes (m.facebook.com → facebook.com)
- Extract handle/ID portion only, store platform separately if needed
- Use URL parsing to handle query parameters and redirects
- Test against real-world samples from veteran org websites

**Phase to address:**
Phase 2 (Scraping Implementation) — add social media URL normalization to enricher.py.

---

### Pitfall 16: Progress Logging Insufficient for Long Jobs

**What goes wrong:**
When scraping 2-5K sites over 10-20 hours, insufficient progress logging makes it impossible to estimate completion time, debug stalls, or identify slow sites. Users cancel jobs thinking they've frozen.

**Prevention:**
- Use tqdm for batch progress bars (already in dependencies)
- Log every 50-100 URLs: processed count, success rate, average time per site
- Track and log slowest domains (>30 seconds per page) for optimization
- Add ETA calculation based on rolling average of recent batch times
- Separate logs: one for high-level progress, one for detailed per-site results
- Consider: send notifications at 25%, 50%, 75% completion for very long jobs

**Phase to address:**
Phase 2 (Scraping Implementation) — add comprehensive progress logging.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Skip robots.txt checking | Faster scraping, simpler code | Legal risk, IP bans, damaged reputation | Never — implementation is simple and essential |
| Use pickle without atomic writes | Easy implementation | Checkpoint corruption, lost progress, restart loops | Never for long-running jobs |
| Single retry strategy for all APIs | Simpler http_client.py | Cascading rate limit failures, poor API optimization | MVP only, must fix before scale |
| No validation on extracted contact info | Faster scraping, no validation overhead | Database filled with junk data, wasted enrichment API calls | Never — validation is critical for data quality |
| BeautifulSoup only (no Playwright) | Much faster, less memory, simpler | Incomplete data from JavaScript-heavy sites | Acceptable if profiling shows target sites are static |
| Full refresh only (no incremental) | Simple implementation | Expensive updates, stale data | Acceptable for MVP, must add for production |
| No memory monitoring in Playwright loops | Simpler code | Crashes after N sites, lost progress | Never for batch processing >100 sites |
| Skip checksum validation on checkpoints | Faster checkpoint saves | Silently corrupt data propagates through pipeline | Never for multi-stage pipelines |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Charity Navigator GraphQL | Requesting all fields in single query (burns quota) | Calculate query cost, batch efficiently, request only needed fields |
| VA Facilities REST | Not handling pagination correctly | Check for next page links, iterate until exhausted |
| Website scraping | Assuming all veteran orgs have modern responsive sites | Many small nonprofits have 10+ year old HTML, test on old sites too |
| ProPublica API | Not handling missing EINs or 404s gracefully | Already working, but validate error handling covers all edge cases |
| Social media extraction | Using single regex for all platforms | Platform-specific patterns (Facebook page vs profile, Twitter vs X) |
| Contact info from headers/footers | Scraping entire page for emails | Target specific sections (header, footer, contact page) for higher precision |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| No batching in Playwright | Memory grows indefinitely | Close/recreate context every 50-100 URLs | After 500-1000 sites |
| Synchronous scraping | 10+ hours for 2K sites | Use asyncio for I/O-bound scraping | Any batch >500 sites |
| No disk caching for API responses | Re-fetching same data on restarts | Use http_client.py disk cache for GET requests | Any job with restarts |
| Full refresh for updates | Days to refresh 80K orgs | Incremental updates with priority scoring | First data refresh after initial load |
| No circuit breaker on rate limits | Thundering herd, endless retries | Pause domain after N consecutive 429s | High-volume scraping (>1000 sites) |
| Pickle checkpoints without versioning | Corrupted checkpoint forces full restart | Keep last 3 checkpoint versions | Long-running jobs (>5 hours) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing API keys in code | Keys exposed in git history, public repos | Use .env with .gitignore (already implemented) |
| Scraping password-protected pages | Legal issues, ethical violations | Only scrape public pages (already compliant) |
| Not masking PII in logs | Sensitive data in log files | Redact emails/phones in debug logs |
| Using same user-agent as browser | Misrepresenting as human user | Identifiable bot user-agent (already implemented) |
| Ignoring HTTPS certificate errors | Man-in-the-middle vulnerability | Validate certificates (requests library default) |
| Exposing scraped data publicly | Privacy violations, GDPR/CCPA issues | Document intended use (supporting nonprofit), limit PII collection |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| No confidence scores on enriched data | Users can't judge data reliability | Add confidence metadata (high/medium/low per field) |
| Duplicate records in output | Confusion, lost trust in data quality | Aggressive deduplication with audit trail |
| Inconsistent data formats | Hard to search/filter (state as "Kentucky" vs "KY") | Strong normalization before output |
| No provenance tracking | Can't verify where data came from | data_sources field already implemented, ensure populated |
| Stale data with no timestamp | Users don't know if org still exists | Add last_updated and data_freshness fields |
| Contact info without validation status | Users waste time on invalid contacts | Add validated flag or remove low-confidence contacts |

---

## "Looks Done But Isn't" Checklist

- [ ] **Web scraping complete:** Verify sample of results manually — check that emails/phones are real, not placeholder text
- [ ] **API integration working:** Verify data enrichment happening — check that API responses contain expected fields, not just status 200
- [ ] **Deduplication effective:** Check duplicate statistics — should merge 15-30% of records for multi-source data
- [ ] **Contact validation:** Spot-check 50 random emails — verify format validity, not just regex match
- [ ] **Rate limiting respected:** Check logs for 429 errors — should be rare (<1% of requests), not frequent
- [ ] **Checkpoint recovery tested:** Simulate crashes and verify resume — don't just test happy path
- [ ] **Memory leaks fixed:** Run scraper for 1000 sites and monitor RAM — should plateau, not climb
- [ ] **Error handling comprehensive:** Check error logs for unhandled exceptions — should have explicit handling for all common errors

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupted checkpoint | LOW | Load previous checkpoint version (if versioned), or restart from last successful stage |
| Over-aggressive deduplication | MEDIUM | Restore pre-dedup data (if preserved), lower threshold, re-run dedup |
| IP banned from rate limit violations | MEDIUM | Wait for ban expiration (usually 24-48 hrs), implement jitter, use proxies |
| Scraped data with placeholder values | HIGH | Must re-scrape affected URLs with fixed selectors, no way to repair bad data |
| Memory exhaustion crashes | LOW | Reduce batch size, add memory monitoring, restart with checkpoints |
| Website structure change | MEDIUM | Update selectors, re-scrape affected sites (if raw HTML stored, just reprocess) |
| API quota exhausted | LOW | Wait for quota reset, implement cost budgeting to prevent recurrence |
| Missing required API key | LOW | Obtain key, add to .env, re-run affected pipeline stage |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent data quality failures | Phase 1: Validation framework | Sample 100 records, manual review shows <5% junk data |
| Memory exhaustion | Phase 1: Batch processing design | Scrape 1000 sites, RAM usage plateaus below 6GB |
| Website structure changes | Phase 2: Multi-pattern selectors, Phase 3: Monitoring | Daily validation runs detect breakage within 24 hours |
| Entity resolution complexity | Phase 1: Confidence scoring, Phase 4: Manual review queue | Dedup stats in expected range (15-30% merged), user feedback positive |
| Rate limit cascading failures | Phase 1: Jitter + circuit breaker | Scrape 2K sites, <1% requests get 429 errors |
| Checkpoint corruption | Phase 1: Atomic writes + versioning | Simulate 10 crashes, all recover successfully |
| Contact validation false positives | Phase 2: Multi-layer validation | Sample 100 contacts, >95% are valid format |
| Incremental update strategy missing | Phase 1: Timestamp + priority design | Can update 10% of dataset in <10% of full refresh time |
| Charity Navigator cost miscalculation | Phase 2: Query cost calculator | API calls stay under quota, no throttling |
| Robots.txt violations | Phase 2: Parser implementation | Logs show 100% domains checked before scraping |
| Schema inconsistency | Phase 2: Enhanced normalizer | All fields match canonical formats in output |
| Playwright performance trade-offs | Phase 2: Hybrid extraction | Static sites use BeautifulSoup, dynamic sites use Playwright |
| VA Facilities API key not configured | Phase 1: Setup validation | Pipeline pre-flight check confirms required keys present |
| NODC extractor outdated | Phase 1: URL validation | Extractor succeeds or explicitly skipped if deprecated |
| Social media URL variations | Phase 2: URL normalization | Duplicate social accounts properly deduplicated |
| Insufficient progress logging | Phase 2: Progress tracking | Users can estimate completion time, identify stalls |

---

## Sources

**Data Quality and Silent Failures:**
- [How to Fix Inaccurate Web Scraping Data: 2026 Best Practices](https://brightdata.com/blog/web-data/fix-inaccurate-web-scraping-data)
- [Web Scraping Monitoring: The Silent Data Quality Crisis](https://medium.com/@arman-bd/web-scraping-monitoring-the-silent-data-quality-crisis-no-one-talks-about-9949a2b5a361)
- [Common Web Scraping Challenges](https://www.blog.datahut.co/post/web-scraping-at-large-data-extraction-challenges-you-must-know)

**Memory and Performance:**
- [Playwright Memory Issues - GitHub #6319](https://github.com/microsoft/playwright/issues/6319)
- [Web Scraping With Playwright](https://www.browserstack.com/guide/playwright-web-scraping)
- [Scalable Web Scraping with Playwright](https://www.browserless.io/blog/scraping-with-playwright-a-developer-s-guide-to-scalable-undetectable-data-extraction)

**Rate Limiting and Retry Logic:**
- [How to Handle API Rate Limits Gracefully (2026 Guide)](https://apistatuscheck.com/blog/how-to-handle-api-rate-limits)
- [Dealing with Rate Limiting Using Exponential Backoff](https://substack.thewebscraping.club/p/rate-limit-scraping-exponential-backoff)
- [Automatic Failover Strategies](https://scrapfly.io/blog/posts/automatic-failover-strategies-for-reliable-data-extraction)

**Entity Resolution and Deduplication:**
- [Entity Resolution Challenges](https://www.sheshbabu.com/posts/entity-resolution-challenges/)
- [Solving Nonprofit Industry CRM Data Management Challenges](https://blog.insycle.com/nonprofit-data-management)
- [Entity Resolution at Scale](https://medium.com/@shereshevsky/entity-resolution-at-scale-deduplication-strategies-for-knowledge-graph-construction-7499a60a97c3)

**Contact Validation:**
- [How to Build a Reliable Contact Scraper](https://www.zenrows.com/blog/contact-scraper)
- [Tackling False Positives in Email Validation](https://www.serviceobjects.com/blog/tackling-false-positives-in-email-validation/)
- [Phone Number Validation](https://www.ipqualityscore.com/solutions/phone-validation)

**Compliance and Legal:**
- [Robots.txt for Web Scraping](https://dataprixa.com/robots-txt-for-web-scraping/)
- [Is Web Scraping Legal in 2025?](https://www.browserless.io/blog/is-web-scraping-legal)
- [Web Scraping Challenges & Compliance](https://groupbwt.com/blog/challenges-in-web-scraping/)

**API Integration:**
- [Charity Navigator's GraphQL API](https://www.charitynavigator.org/products-and-services/graphql-api/)
- [VA Facilities API Documentation](https://developer.va.gov/explore/facilities/docs/facilities)
- [Understanding GitHub API Rate Limits: REST, GraphQL, and Beyond](https://github.com/orgs/community/discussions/163553)

**Data Pipeline Patterns:**
- [Full Refresh vs Incremental Refresh in ETL](https://airbyte.com/data-engineering-resources/full-refresh-vs-incremental-refresh)
- [Building Efficient Data Pipelines With Incremental Updates](https://www.fivetran.com/blog/building-efficient-data-pipelines-with-incremental-updates)

**Nonprofit Data Standards:**
- [Common Data Model for Nonprofits](https://learn.microsoft.com/en-us/industry/nonprofit/common-data-model-for-nonprofits)
- [Nonprofit Data Management](https://www.ccsfundraising.com/insights/nonprofit-data-management/)

---

*Pitfalls research for: Veteran Organization Directory — Nonprofit Data Enrichment with Web Scraping and API Integration*
*Researched: 2026-02-11*
*Context: 80K+ veteran orgs, Kentucky subset scraping (2-5K orgs), BeautifulSoup + Playwright stack, existing checkpoint/rate-limiting infrastructure*

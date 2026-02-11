# Codebase Concerns

**Analysis Date:** 2026-02-11

## Tech Debt

**Broad Exception Handling (Silent Failures)**
- Issue: Multiple extractors catch bare `Exception` and log warnings, but don't distinguish between network errors, data format errors, and parsing failures. This masks actual problems and makes debugging difficult.
- Files: `extractors/nrd.py:48`, `extractors/nrd.py:56`, `extractors/charity_nav.py:89`, `extractors/propublica.py:57`, `extractors/va_vso.py:102`, `extractors/va_vso.py:151`, `extractors/va_facilities.py:49`, `extractors/nodc.py:44`, `extractors/nodc.py:76`, `transformers/enricher.py:90`, `transformers/normalizer.py:56`, `loaders/deduplicator.py:162`
- Impact: Pipeline continues with incomplete data without visibility into what failed. Silent data loss risk.
- Fix approach: Replace broad exception handlers with specific exception types (requests.RequestException, ValueError, KeyError, json.JSONDecodeError). Log severity levels appropriately (error vs warning). Consider retry logic for transient failures.

**Pickle-Based Checkpointing (Security & Compatibility Risk)**
- Issue: Checkpoints use `pickle.dump()` which is insecure for untrusted data and incompatible across Python versions.
- Files: `utils/checkpoint.py:16-22`, `utils/checkpoint.py:25-37`
- Impact: Checkpoints from different Python versions won't load. Potential code injection if checkpoint files are modified. Recovery from corruption requires manual deletion.
- Fix approach: Replace pickle with JSON or Parquet for checkpoints. JSON for metadata (lists of processed EINs), Parquet for DataFrames.

**No Input Validation on Pipeline Arguments**
- Issue: `main.py` accepts `--stages 1,2,5` but doesn't validate stage numbers or handle malformed input (e.g., `--stages 1,99,abc`).
- Files: `main.py:214-217`
- Impact: User passes invalid stages silently, pipeline runs wrong subset. No warning about invalid input.
- Fix approach: Validate stage input against set(1-8), raise ArgumentError if invalid.

**Exposed API Keys in Settings (Default Values)**
- Issue: `config/settings.py` defines empty string defaults for `CHARITY_NAV_API_KEY` and `VA_FACILITIES_API_KEY`. If `.env` is missing, extractors silently skip instead of warning about missing critical data.
- Files: `config/settings.py:33`, `config/settings.py:38`
- Impact: Silent data loss. User doesn't know VA Facilities and Charity Navigator data are missing until much later.
- Fix approach: Use sentinel values (e.g., `None`) instead of empty strings. Check at stage 2 and 4 init time and warn/fail explicitly.

**Hard-Coded Rate Limits Not Matching Reality**
- Issue: Rate limits are set in code and don't adjust based on API responses (rate limit headers, 429 responses).
- Files: `config/settings.py:29`, `config/settings.py:34`, `config/settings.py:39`, `config/settings.py:46`, `config/settings.py:62`
- Impact: May hit rate limits despite configured limits. May be unnecessarily slow.
- Fix approach: Implement exponential backoff in `utils/http_client.py` based on 429 responses and Retry-After headers.

## Known Bugs

**NODC URLs Outdated (Non-Functional)**
- Symptoms: Stage 4 logs "No NODC data files yielded results" or "Could not process NODC file". Directory is missing mission statements and employee counts that NODC could provide.
- Files: `extractors/nodc.py:21-25`, `extractors/nodc.py:47-78`
- Trigger: Run full pipeline. NODC extractor always returns empty DataFrame.
- Cause: GitHub repository structure changed; URLs point to files that no longer exist in those locations.
- Workaround: None. Stage skipped automatically when no data available.

**VA Facilities and Charity Navigator Require Undocumented API Keys**
- Symptoms: Stages 2 and 4 silently return empty DataFrames. No error visible unless looking at logs.
- Files: `extractors/charity_nav.py:67-71`, `extractors/va_facilities.py:36-41`
- Trigger: Run pipeline without setting env vars `CHARITY_NAVIGATOR_API_KEY` or `VA_FACILITIES_API_KEY`.
- Cause: Free API keys available but not documented in README. CLAUDE.md mentions they're needed but not how to obtain them.
- Workaround: Obtain API keys from Charity Navigator and VA Lighthouse and set as env vars.

**ProPublica num_employees Incorrect**
- Symptoms: `num_employees` field shows form filing count (typically 1, 2, or 3), not actual employee count.
- Files: `extractors/propublica.py:88`
- Trigger: Check any org with ProPublica data. `num_employees: 1` when org has thousands.
- Cause: ProPublica API returns `number_of_forms_filed` (how many years of 990s filed), not employee count.
- Workaround: Ignore `num_employees` from ProPublica source; use NODC or leave null.

**Deduplicator Merge Strategy Can Lose Data**
- Symptoms: When merging duplicate records, only first non-null value per column is kept. If org has multiple phone numbers or websites, only one is preserved.
- Files: `loaders/deduplicator.py:28-48`
- Trigger: Two records for same org with different phones/websites. After merge, only first one kept.
- Cause: `_merge_rows()` uses `iloc[0]` then fills blanks; doesn't aggregate multiple values.
- Workaround: None. Data loss is silent.

**HTTP Cache Never Expires**
- Symptoms: If API endpoint data changes, cached response is used forever.
- Files: `utils/http_client.py:73-88`
- Trigger: Run pipeline, then API data updates, then run pipeline again. Old cached data used.
- Cause: Cache is file-based with no TTL. Only removed via `--clean`.
- Workaround: Delete `data/http_cache/` before rerunning specific stages.

**Email Extraction Overly Broad**
- Symptoms: Web scraping captures support@squarespace.com, sentry@sentry.io and generic platform emails.
- Files: `transformers/enricher.py:44-47`
- Trigger: Org website built on Squarespace. `email` field shows vendor email, not org contact.
- Cause: SKIP_EMAILS list is incomplete. Platform emails still slip through.
- Workaround: Implement domain blacklist for known providers.

## Security Considerations

**No Request Timeout on Streaming Downloads**
- Risk: `utils/http_client.py:120-130` streams file downloads with timeout set, but infinite loops on slow servers could hang pipeline.
- Files: `utils/http_client.py:120-130`
- Current mitigation: `timeout` param is set, but only applies to initial connection, not read timeout.
- Recommendations: Add read timeout per chunk. Add max file size limit.

**No HTTPS Certificate Validation Override**
- Risk: Currently none, but requests library default is safe. However, code could be modified to disable cert validation under pressure.
- Files: `utils/http_client.py`
- Current mitigation: Using requests library defaults (validate=True).
- Recommendations: Explicitly set `verify=True` in all session mounts.

**Checkpoint Files Stored in Repo Directory**
- Risk: If checkpoints accidentally committed, they may contain sensitive data (API responses, org names, EINs).
- Files: `data/checkpoints/` (in .gitignore, but risk if .gitignore changes)
- Current mitigation: `.gitignore` covers `data/` directory.
- Recommendations: Ensure `data/checkpoints/` is in .gitignore explicitly.

**No Input Sanitization on Org Names**
- Risk: Org names are scraped from the web and used directly in CSV/logs. Could contain escape sequences, null bytes, or commands.
- Files: All extractors that process `org_name`
- Current mitigation: Python strings handle nulls safely. CSV encoding is UTF-8.
- Recommendations: Add basic validation (strip non-printable chars) in schema coercion.

## Performance Bottlenecks

**ProPublica API Extraction (5–8 hours for 80K EINs)**
- Problem: Fetching all EINs from ProPublica one-at-a-time takes very long.
- Files: `extractors/propublica.py:52-66`
- Cause: Rate-limited to 2 req/sec. 80K EINs × 0.5s per EIN = ~40K seconds ≈ 11 hours worst-case.
- Improvement path: Use batch endpoints if available. Implement asyncio for concurrent requests respecting rate limit.

**Web Enrichment (Stage 7) is Extremely Slow (10–20+ hours)**
- Problem: Scraping 80K websites at 0.5 req/sec = 160K seconds ≈ 44 hours.
- Files: `transformers/enricher.py:61-110`, `main.py:150-160`
- Cause: Sequential scraping with 0.5 req/sec rate limit (2 second minimum per request).
- Improvement path: Increase rate limit if target servers support it (they likely do). Use asyncio. Consider sampling (scrape 10% random sample instead of all).

**Deduplication Tier 2 (Fuzzy Matching) is O(n²)**
- Problem: Every city+state group runs fuzzy comparison on all pairs. Large groups (cities with many orgs) become very slow.
- Files: `loaders/deduplicator.py:91-115`
- Cause: Nested loop with `fuzz.token_sort_ratio()` on every pair.
- Improvement path: Use string similarity index (BK-tree) to reduce comparisons. Or implement probabilistic matching (MinHash).

**Merger Iterates Over Merged Rows Multiple Times**
- Problem: `_smart_merge_on_ein()` iterates over merged DataFrame multiple times to update data_sources.
- Files: `loaders/merger.py:103-114`
- Cause: Row-by-row manipulation instead of vectorized operation.
- Improvement path: Vectorize data_sources merge using `groupby()` and `apply()`.

**DataFrame Concatenation Not Optimized**
- Problem: `pd.concat()` is called multiple times, each creates new copy of entire DataFrame.
- Files: `loaders/merger.py:66`, `loaders/deduplicator.py:71`, `loaders/deduplicator.py:141`, `loaders/deduplicator.py:186`
- Cause: No use of append optimization or pre-allocation.
- Improvement path: Use list accumulation then single concat. Or use Parquet appends.

## Fragile Areas

**CSV Writer Confidence Scoring**
- Files: `loaders/csv_writer.py:19-33`
- Why fragile: Confidence weights hardcoded in `config/schema.py:CONFIDENCE_WEIGHTS`. If schema changes, weights must be manually updated. No validation that weights sum to 1.0 or that all weighted columns exist.
- Safe modification: Create ConfigWeights class. Validate at schema load time.
- Test coverage: Confidence scoring has no tests. Unknown if weights are correct or produce expected 0.0–1.0 range.

**Deduplicator Data Type Assumptions**
- Files: `loaders/deduplicator.py:28-186`
- Why fragile: Uses `str.upper()` and `.replace()` on columns without checking if columns are strings. If normalizer fails to convert state to string, deduplicator crashes.
- Safe modification: Validate column dtypes before deduplication. Coerce to string.
- Test coverage: No unit tests for deduplicator. Unknown if it handles edge cases (empty columns, all-null columns, non-ASCII names).

**Web Enrichment Email Extraction**
- Files: `transformers/enricher.py:138-146`
- Why fragile: Simple regex with hardcoded skip list. Easily breaks if email format changes or new platforms added.
- Safe modification: Use email-validator library instead of regex. Maintain skip-list in config.
- Test coverage: No tests. Unknown performance on real websites.

**NRD Sitemap Parsing Has Fallback Without Namespace**
- Files: `extractors/nrd.py:140-150`
- Why fragile: Attempts XML namespace parsing, then falls back to text iteration. Fallback is crude and may capture non-URL text.
- Safe modification: Use standard XML parsing library (lxml or xml.etree with proper namespace handling).
- Test coverage: No tests for sitemap parsing.

**Base Extractor Data Sources Tagging**
- Files: `extractors/base_extractor.py:48-55`
- Why fragile: Builds `data_sources` string by checking if name exists in field. If extractor name appears in an org's actual name, it will falsely detect duplication.
- Safe modification: Use a structured field (list or JSON array) instead of concatenated string.
- Test coverage: No tests for data sources logic.

**Normalizer Phone Number Regex**
- Files: `transformers/normalizer.py:26-35`
- Why fragile: Assumes 10-digit US phone. Fails on extensions, international formats, or non-standard formats.
- Safe modification: Use phonenumbers library instead of regex.
- Test coverage: No tests for phone normalization.

## Scaling Limits

**Pipeline Memory Usage with 80K+ Records**
- Current capacity: Holds entire DataFrame in RAM. ~80K orgs × 50 columns × 100 bytes/cell ≈ 400 MB expected, but actual usage may be 1–2 GB due to string overhead.
- Limit: If dataset grows to 1M+ records, memory exhaustion possible.
- Scaling path: Switch to Polars (more efficient) or stream Parquet instead of loading full DataFrame.

**Checkpoint File Size**
- Current capacity: Each checkpoint is a pickled DataFrame. For 80K orgs: ~100–500 MB per checkpoint.
- Limit: If checkpoints accumulate (7 stages × 500 MB = 3.5 GB), disk space fills up.
- Scaling path: Implement checkpoint retention (keep only last N). Switch to Parquet format (more compact).

**Rate Limiting Doesn't Support Burst Capacity**
- Current capacity: Fixed rate (2 req/sec for ProPublica) means pipeline is bottlenecked regardless of API capacity.
- Limit: API may support 10+ req/sec but code limits to 2.
- Scaling path: Implement token bucket algorithm. Respect rate-limit headers from API.

**No Pagination or Streaming for Large Result Sets**
- Current capacity: NRD sitemap loads all 7,900 URLs into memory before processing.
- Limit: If NRD or other sources grow to 100K+ resources, memory exhaustion possible.
- Scaling path: Stream URLs and process one at a time instead of loading full sitemap.

## Dependencies at Risk

**BeautifulSoup Parser (lxml)**
- Risk: Code uses `BeautifulSoup(html, "lxml")` which requires lxml to be installed. If lxml is missing or broken, all HTML parsing fails silently (falls back to html.parser, which is slower and less robust).
- Files: `extractors/va_vso.py:58`, `extractors/nrd.py:106`, `extractors/nrd.py:119`, `transformers/enricher.py:119`, `transformers/normalizer.py:51`
- Impact: Web scraping silently produces garbage output. Deduplication fails on malformed URLs.
- Migration plan: Explicitly check lxml is installed at import. Use html.parser as documented fallback. Better: specify parser explicitly in dependencies.

**Pandas .get() Method Non-Standard**
- Risk: Code uses `df.get(column_name)` which is not standard Pandas. Should be `df[column_name]` or `df.get(column_name, default)`. This works in current Pandas but may break in future versions.
- Files: `extractors/charity_nav.py:157`, `loaders/merger.py:105`
- Impact: Breaking upgrade to new Pandas version.
- Migration plan: Replace with standard `df[col]` or `df.get(col, pd.Series())`.

**Rapidfuzz Version Not Pinned**
- Risk: `rapidfuzz` is used for fuzzy matching but version is not pinned in requirements. Algorithm could change between versions.
- Files: `loaders/deduplicator.py:7`, `loaders/deduplicator.py:106`
- Impact: Deduplication results differ between runs with different rapidfuzz versions.
- Migration plan: Pin rapidfuzz version in requirements-pipeline.txt.

**Requests Library 3.0 Breaking Changes**
- Risk: Requests library is in transition. Code uses patterns that may break in v3.0 (e.g., response._content).
- Files: `utils/http_client.py:97`
- Impact: Breaking upgrade to requests 3.0.
- Migration plan: Use response.content (property) instead of response._content (private).

## Missing Critical Features

**No Logging to File During Web Scraping (Stage 7)**
- Problem: Web enrichment runs for 10+ hours with no persistent log. If process crashes, no visibility into what happened.
- Blocks: Cannot debug slow scraping. Cannot resume from specific URLs.
- Fix: Add persistent log file for enricher progress. Implement true resumability per-URL not just "done/not done".

**No Health Checks for External APIs**
- Problem: Pipeline can run for 8+ hours before discovering ProPublica API is down. By then, hours wasted on IRS download and other stages.
- Blocks: Cannot fail fast. Cannot detect API outages early.
- Fix: Add `--health-check` flag to test each API before starting pipeline.

**No Data Validation Between Stages**
- Problem: If Stage 2 produces garbage data, it propagates through to final output without warning.
- Blocks: Cannot catch data quality regressions early.
- Fix: Add schema validation + sanity checks between each stage (e.g., "at least 50% of EINs should have revenue data").

**No Support for Incremental Updates**
- Problem: Pipeline is all-or-nothing. Cannot update just ProPublica data for changed orgs; must rerun everything.
- Blocks: Cannot do daily/weekly incremental refreshes.
- Fix: Implement delta mode: detect what changed, re-fetch only those EINs, merge with existing output.

**No Deduplication Within ProPublica Results**
- Problem: If ProPublica returns duplicate records, they're not deduplicated until Stage 6. By then, merge logic may have created separate rows.
- Blocks: Final output may contain exact duplicates from ProPublica source.
- Fix: Deduplicate within each extractor before returning. Or deduplicate immediately after each source merge.

## Test Coverage Gaps

**Untested Deduplication Logic**
- What's not tested: All three tiers of deduplication. Edge cases (all-null columns, non-ASCII names, empty org_name).
- Files: `loaders/deduplicator.py`
- Risk: Silent data loss. Merging strategy could be wrong.
- Priority: High

**Untested Merger Priority Logic**
- What's not tested: Whether SOURCE_PRIORITY is respected. If two sources provide different values for same field, does higher-priority value win?
- Files: `loaders/merger.py:17-26`, `loaders/merger.py:93-100`
- Risk: Data loss. Lower-priority source overwrites higher-priority.
- Priority: High

**No Tests for Schema Coercion**
- What's not tested: Whether all columns are properly coerced to expected dtypes. What happens with malformed EINs, revenues, etc.
- Files: `config/schema.py`
- Risk: Type errors downstream.
- Priority: Medium

**No Tests for Pipeline Resumability**
- What's not tested: Whether --resume flag actually resumes from correct checkpoint. Whether partial checkpoints corrupt recovery.
- Files: `main.py`, `utils/checkpoint.py`, all extractors with checkpointing
- Risk: Users lose work if resume doesn't work.
- Priority: High

**No Tests for Web Enrichment**
- What's not tested: Email extraction, social media URL matching, error handling on unreachable sites.
- Files: `transformers/enricher.py`
- Risk: Stage 7 data quality unknown until pipeline completes (8+ hours).
- Priority: Medium

**No Tests for Normalizers**
- What's not tested: Phone formatting, address normalization, URL normalization on edge cases.
- Files: `transformers/normalizer.py`
- Risk: Final output has incorrectly formatted data.
- Priority: Medium

---

*Concerns audit: 2026-02-11*

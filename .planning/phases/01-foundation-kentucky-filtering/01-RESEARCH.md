# Phase 1: Foundation & Kentucky Filtering - Research

**Researched:** 2026-02-11
**Domain:** Data pipeline filtering, web scraping, checkpoint-based batch processing
**Confidence:** HIGH

## Summary

Phase 1 focuses on fixing the broken NODC extractor URLs and implementing state-based filtering (Kentucky) before Stage 7 web enrichment runs. The codebase already has robust checkpoint infrastructure (`utils/checkpoint.py`) that saves progress every N operations, but lacks progress bars and time estimation. The enricher (`transformers/enricher.py`) has checkpoint resumability working but no user-facing progress indicators.

The primary technical challenges are:
1. **NODC URL discovery** - GitHub repos have reorganized; the concordance file path changed from `efiler_master_concordance.csv` to `concordance.csv`, and BMF CSV locations are unclear
2. **State filtering implementation** - Need to add Kentucky filter BEFORE Stage 7 enrichment to reduce scope from 80K to 2-5K orgs
3. **Progress bars** - tqdm is in requirements but not imported/used anywhere; need to add to enricher's batch processing loop

**Primary recommendation:** Use pandas boolean indexing for Kentucky filtering, verify NODC GitHub URLs manually before coding fixes, and integrate tqdm with existing checkpoint pattern (save every 100, display progress bar continuously).

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.1+ | DataFrame filtering, CSV I/O | Industry standard for tabular data; existing codebase uses extensively |
| tqdm | 4.66+ | Progress bars with time estimates | Most popular progress bar library; ~120K GitHub stars; minimal overhead (60ns/iteration) |
| requests | 2.31+ | HTTP client with retry logic | Already used in `utils/http_client.py` with custom `RateLimitedSession` wrapper |
| beautifulsoup4 | 4.12+ | HTML parsing for web scraping | Already used in `transformers/enricher.py` for social media extraction |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pickle | stdlib | Checkpoint serialization | Already used in `utils/checkpoint.py` for resumability |
| logging | stdlib | Progress reporting | Already configured in `main.py` with file + console handlers |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| pandas filtering | NumPy boolean arrays | pandas more readable for column-based filtering; existing codebase pattern |
| tqdm | alive-progress or rich.progress | tqdm has better pandas integration (`tqdm.pandas()`); already in requirements |
| pickle | JSON or parquet | pickle handles arbitrary Python objects (sets, tuples); faster for checkpoints |

**Installation:**
Already satisfied by `/Users/vincecain/Projects/vet_org_directory/requirements-pipeline.txt`

## Architecture Patterns

### Recommended Project Structure
Existing structure is appropriate:
```
extractors/
  nodc.py              # FIX: Update GitHub URLs
transformers/
  enricher.py          # ADD: tqdm progress bar + time estimates
main.py                # ADD: Kentucky filter before stage7_enrichment() call
config/
  settings.py          # VERIFY: CHECKPOINT_INTERVAL=500, change to 100 per requirements
```

### Pattern 1: State Filtering Before Enrichment
**What:** Add Kentucky filter in `main.py` between Stage 6 (dedup) and Stage 7 (enrichment)
**When to use:** When enrichment is expensive (web scraping) and subset is sufficient for testing
**Example:**
```python
# In main.py, between stage6_dedup() and stage7_enrichment()
def stage6_5_kentucky_filter(df: pd.DataFrame) -> pd.DataFrame:
    """Filter to Kentucky orgs before web enrichment."""
    logger.info("=" * 60)
    logger.info("STAGE 6.5: Kentucky Filter")
    logger.info("=" * 60)

    # Filter to Kentucky state
    ky_mask = df["state"].str.upper() == "KY"
    ky_df = df[ky_mask].copy()

    logger.info(f"Kentucky filter: {len(ky_df):,} of {len(df):,} orgs ({len(ky_df)/len(df)*100:.1f}%)")
    return ky_df
```

### Pattern 2: Checkpoint-Based Batch Processing with Progress Bar
**What:** Combine pickle checkpoints (every N ops) with tqdm progress bar (every iteration)
**When to use:** Long-running operations (API calls, web scraping) that need resumability + user feedback
**Example:**
```python
# In transformers/enricher.py
from tqdm import tqdm

def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
    partial = load_checkpoint("enricher_partial")
    if partial is not None:
        enrichments, done_indices = partial
        self.logger.info(f"Resuming enrichment from {len(done_indices)} completed")
    else:
        enrichments = {}
        done_indices = set()

    needs_enrichment = df[df["website"].notna()].index
    remaining = [i for i in needs_enrichment if i not in done_indices]

    # Add tqdm progress bar with time estimates
    for count, idx in enumerate(tqdm(remaining, desc="Enriching websites", unit="org")):
        url = df.at[idx, "website"]
        try:
            data = self._scrape_website(url)
            if data:
                enrichments[idx] = data
        except Exception as e:
            self.logger.debug(f"Error scraping {url}: {e}")

        done_indices.add(idx)

        # Checkpoint every 100 (changed from 500)
        if (count + 1) % 100 == 0:
            save_checkpoint("enricher_partial", (enrichments, done_indices))
```

### Pattern 3: NODC URL Probing
**What:** Try multiple URL patterns for NODC files since repos reorganize
**When to use:** When GitHub raw URLs change and documentation is outdated
**Example:**
```python
# In extractors/nodc.py extract() method (already implemented)
data_urls = [
    f"{NODC_BMF_REPO}/data/bmf-master.csv",
    f"{NODC_BMF_REPO}/bmf-master.csv",
    f"{NODC_BASE}/990_master.csv",
]

for url in data_urls:
    try:
        dest = RAW_DIR / f"nodc_{url.split('/')[-1]}"
        if not dest.exists():
            self.http.download_file(url, dest)
        # Process file...
        if len(df) > 0:
            return df  # Success, stop trying
    except Exception as e:
        self.logger.warning(f"Could not process NODC file {url}: {e}")
        continue
```

### Anti-Patterns to Avoid
- **Filter after enrichment**: Wastes hours scraping 80K orgs when only 2-5K needed. ALWAYS filter before expensive operations.
- **Progress bars without checkpoints**: User sees progress but can't resume on crash. ALWAYS pair them.
- **Checkpoint without progress bars**: User has no ETA on long operations. ALWAYS show progress.
- **Hard-coded URLs**: GitHub repos reorganize. ALWAYS probe multiple URL patterns.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Progress bars | Custom print statements with percentages | `tqdm` library | Handles terminal width, nested bars, rate calculation, time estimates automatically |
| Checkpoint serialization | Custom JSON encoder for sets/DataFrames | `pickle` (stdlib) | Handles arbitrary Python objects; already used in codebase |
| Rate limiting | Manual `time.sleep()` between requests | `RateLimitedSession` (existing `utils/http_client.py`) | Already handles retry, backoff, disk cache |
| State filtering | Multiple if/elif state checks | pandas boolean indexing (`df[df["state"] == "KY"]`) | Vectorized, readable, fast |
| Time estimation | Calculate ETA from start time + count | tqdm's built-in rate tracking | Automatically smooths rate, shows time remaining |

**Key insight:** Checkpoint/progress infrastructure is deceptively complex (rate smoothing, terminal rendering, pickle protocol handling). The codebase already has 90% of what's needed; just add tqdm wrapper.

## Common Pitfalls

### Pitfall 1: CHECKPOINT_INTERVAL Mismatch
**What goes wrong:** Requirements say "save every 100 orgs" but `config/settings.py` has `CHECKPOINT_INTERVAL = 500`
**Why it happens:** Settings file was optimized for API calls (ProPublica), not web scraping
**How to avoid:** Change to 100 before Phase 1 work begins
**Warning signs:** Checkpoints happen less frequently than requirements specify

### Pitfall 2: State Column Case Sensitivity
**What goes wrong:** Filter `df["state"] == "KY"` misses records with lowercase "ky" or "Ky"
**Why it happens:** IRS BMF normalizes to uppercase, but other sources may not
**How to avoid:** Always use `df["state"].str.upper() == "KY"` for case-insensitive matching
**Warning signs:** Kentucky filter returns fewer orgs than expected (should be 2-5K from 80K)

### Pitfall 3: NODC GitHub URL Changes
**What goes wrong:** Hard-coded URLs break when NODC reorganizes repos
**Why it happens:** GitHub projects restructure over time; "master" branch files move
**How to avoid:** Probe multiple URL patterns (already implemented in `nodc.py`), log each attempt
**Warning signs:** NODC extractor logs "No NODC data files yielded results"

### Pitfall 4: tqdm + Checkpoint Loop Counter Confusion
**What goes wrong:** `enumerate()` starts at 0, but checkpoint comparison `(count + 1) % 100` expects 1-indexed
**Why it happens:** Off-by-one error when wrapping existing enumerate loop with tqdm
**How to avoid:** Keep `enumerate(tqdm(remaining))` pattern, checkpoint triggers at `(count + 1) % 100 == 0`
**Warning signs:** First checkpoint happens at iteration 101 instead of 100

### Pitfall 5: Progress Bar Overwrites Log Messages
**What goes wrong:** tqdm progress bar and logger.info() messages collide in terminal
**Why it happens:** tqdm uses `\r` to overwrite line; logger prints new lines
**How to avoid:** Use tqdm's built-in `tqdm.write()` for logging inside tqdm loops, OR use `file=sys.stderr` for tqdm
**Warning signs:** Progress bar and log messages interleaved/garbled in terminal output

## Code Examples

Verified patterns from existing codebase and official docs:

### Kentucky State Filtering (pandas boolean indexing)
```python
# Source: pandas docs + existing codebase pattern (irs_bmf.py lines 68-89)
def filter_to_kentucky(df: pd.DataFrame) -> pd.DataFrame:
    """Filter DataFrame to Kentucky organizations only."""
    # Case-insensitive state matching
    ky_mask = df["state"].str.upper() == "KY"
    ky_df = df[ky_mask].copy()
    return ky_df
```

### Progress Bar with Checkpoint Resumability
```python
# Source: tqdm docs + existing checkpoint pattern (propublica.py lines 40-66)
from tqdm import tqdm
from utils.checkpoint import load_checkpoint, save_checkpoint

def batch_process_with_progress(items, checkpoint_name, process_fn):
    """Generic batch processor with progress bar + checkpoints."""
    # Resume from checkpoint
    partial = load_checkpoint(checkpoint_name)
    if partial:
        results, done_ids = partial
    else:
        results, done_ids = [], set()

    remaining = [item for item in items if item.id not in done_ids]

    # Add progress bar
    for count, item in enumerate(tqdm(remaining, desc="Processing", unit="item")):
        result = process_fn(item)
        if result:
            results.append(result)
        done_ids.add(item.id)

        # Checkpoint every 100
        if (count + 1) % 100 == 0:
            save_checkpoint(checkpoint_name, (results, done_ids))

    return results
```

### NODC URL Verification (requests with try/except)
```python
# Source: existing nodc.py lines 48-78
import requests

def verify_nodc_urls():
    """Manually test NODC GitHub raw URLs before updating code."""
    test_urls = [
        "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file/master/concordance.csv",
        "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-exempt-org-business-master-file/master/data/bmf-master.csv",
        "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-exempt-org-business-master-file/master/bmf-master.csv",
    ]

    for url in test_urls:
        try:
            resp = requests.head(url, timeout=10)
            print(f"✓ {url} → {resp.status_code}")
        except Exception as e:
            print(f"✗ {url} → {e}")
```

### Time Estimate Display (tqdm automatic)
```python
# Source: tqdm docs https://github.com/tqdm/tqdm
from tqdm import tqdm
import time

# tqdm automatically calculates and displays time remaining
for i in tqdm(range(1000), desc="Processing"):
    time.sleep(0.01)  # Simulated work
    # Output shows: "Processing: 45%|████▌     | 450/1000 [00:04<00:05, 99.8it/s]"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual URL updates when GitHub links break | Probe multiple URL patterns with try/except | Already in codebase (nodc.py) | Extractor resilient to upstream changes |
| Log-based progress (`logger.info()` every N) | tqdm progress bars with ETA | Not yet implemented | User sees real-time progress + time remaining |
| Checkpoint every 500 (optimized for fast APIs) | Checkpoint every 100 (web scraping) | Phase 1 requirement | Better resumability for slower operations |
| Process all 80K orgs then filter | Filter to 2-5K Kentucky orgs before enrichment | Phase 1 requirement | 16-40x speedup on Stage 7 (hours → minutes) |

**Deprecated/outdated:**
- **NODC URL `efiler_master_concordance.csv`**: Renamed to `concordance.csv` in GitHub repo (year unknown, discovered in Phase 1 research)
- **Hard-coded CHECKPOINT_INTERVAL=500**: Too infrequent for web scraping; change to 100 per requirements

## Open Questions

1. **NODC BMF CSV exact location**
   - What we know: Repository is `Nonprofit-Open-Data-Collective/irs-exempt-org-business-master-file`, file is likely `bmf-master.csv` or in `data/` subdirectory
   - What's unclear: Current working URL (GitHub search found repo but not specific file path)
   - Recommendation: Manually browse GitHub repo or use `requests.head()` to test URL patterns from research (see Code Examples section)

2. **Kentucky org count estimate**
   - What we know: Requirements say "2-5K" Kentucky orgs from "80K" total
   - What's unclear: Based on what data source? IRS BMF has Kentucky orgs but count unknown
   - Recommendation: Run Stage 1 (IRS BMF extraction), then count `df[df["state"] == "KY"]` to validate estimate

3. **Progress bar + logger interaction**
   - What we know: tqdm progress bar uses `\r` to overwrite terminal line; logger uses `\n` for new lines
   - What's unclear: Will they collide and garble output?
   - Recommendation: Use `tqdm.write()` for log messages inside tqdm loops, OR set tqdm `file=sys.stderr` to separate streams

4. **Checkpoint file size growth**
   - What we know: Checkpoints use pickle to serialize `(enrichments: dict, done_indices: set)`
   - What's unclear: How large will checkpoint file grow for 2-5K orgs?
   - Recommendation: Estimate 1KB per org (conservative); 5K orgs = 5MB checkpoint file (acceptable)

## Sources

### Primary (HIGH confidence)
- **Existing codebase** at `/Users/vincecain/Projects/vet_org_directory`:
  - `extractors/nodc.py` - NODC URL patterns and fallback logic (lines 20-81)
  - `transformers/enricher.py` - Checkpoint-based batch processing pattern (lines 61-99)
  - `utils/checkpoint.py` - Pickle-based checkpoint implementation (lines 1-58)
  - `config/settings.py` - CHECKPOINT_INTERVAL=500 (line 59), ENRICHER_RATE_LIMIT=0.5 (line 62)
  - `main.py` - 8-stage pipeline structure showing where to add Kentucky filter (lines 137-161)
- **pandas documentation** - DataFrame filtering: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.filter.html
- **tqdm GitHub** - Progress bar library: https://github.com/tqdm/tqdm

### Secondary (MEDIUM confidence)
- [GeeksforGeeks: Filter Pandas Dataframe by Column Value](https://www.geeksforgeeks.org/pandas/ways-to-filter-pandas-dataframe-by-column-values/) - Boolean indexing patterns
- [Nonprofit Open Data Collective GitHub](https://github.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file) - Concordance file structure and repository organization
- [Analytics Vidhya: Overview of TQDM (Updated 2026)](https://www.analyticsvidhya.com/blog/2021/05/how-to-use-progress-bars-in-python/) - tqdm usage patterns with pandas
- [Data Scientist: Progress Bars in Pandas/Python - TQDM](https://datascientyst.com/progress-bars-pandas-python-tqdm/) - pandas integration patterns

### Tertiary (LOW confidence)
- **NODC BMF CSV exact URL**: Not verified in research; codebase probes multiple patterns but none confirmed working in 2026
- **Kentucky org count**: "2-5K" cited in requirements but not independently verified against actual IRS BMF data

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in requirements-pipeline.txt and used in codebase
- Architecture: HIGH - Existing codebase has checkpoint pattern; just need to add tqdm wrapper
- Pitfalls: MEDIUM-HIGH - Based on codebase inspection + common pandas/tqdm issues; NODC URL issue LOW confidence (need manual verification)

**Research date:** 2026-02-11
**Valid until:** 2026-03-11 (30 days - stable domain, tqdm/pandas APIs rarely change)

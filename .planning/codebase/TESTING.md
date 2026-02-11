# Testing Patterns

**Analysis Date:** 2026-02-11

## Test Framework

**Status:** No automated testing infrastructure detected

**Finding:** No test files, test configuration, or test dependencies observed.
- No `pytest.ini`, `setup.cfg`, `tox.ini`, or `pyproject.toml` with test config
- No `tests/`, `test_*.py`, or `*_test.py` files in codebase
- No test runners (pytest, unittest, etc.) in `requirements-pipeline.txt`

**Implication:** All validation is manual or production-time (pipeline execution itself is the validation).

## Current Validation Approach

**Pipeline as validation:**

The 8-stage pipeline in `main.py` (lines 40-174) serves as the primary validation mechanism. Each stage:
1. Logs counts and metrics that indicate success/failure
2. Persists intermediate checkpoints (enables resume on failure)
3. Raises exceptions on critical errors (HTTP 5xx, missing files)

**Stage validation examples:**

**Stage 1 (`stage1_irs_bmf`):** `extractors/irs_bmf.py` lines 40-66
- Downloads IRS BMF files from URLs
- Logs file counts: "Loaded {filename}: {len(df):,} rows"
- Applies three-tier filter with logged results:
  - "NTEE W-prefix matches: X"
  - "501(c)(19) matches: Y"
  - "Keyword name matches: Z"
- Final log: "Veteran-filtered records: {len(filtered):,}"
- Failure case: logs and returns empty DataFrame if download fails

**Stage 2 (`stage2_api_enrichment`):** `extractors/propublica.py` lines 38-68
- Iterates over EIN list with per-EIN try-catch
- Logs failures as warnings: `logger.warning(f"Error fetching EIN {ein}: {e}")`
- Checkpoints every 500 EINs: `logger.info(f"ProPublica progress: {len(done_eins):,}/{len(self.ein_list):,}")`
- Returns DataFrame with whatever records succeeded (partial data acceptable)

**Deduplication validation:** `loaders/deduplicator.py` lines 12-25
- Each tier logs record counts before/after:
  ```python
  logger.info(f"After EIN dedup: {len(df):,} records")
  logger.info(f"After fuzzy name+city dedup: {len(df):,} records")
  logger.info(f"After URL domain dedup: {len(df):,} records")
  ```
- Tier output becomes input for next tier (pipeline validation)

## Error Handling (Validation via Exception)

**Pattern: Fail-fast for critical errors, continue for recoverable**

**HTTP errors:**
`utils/http_client.py` lines 90-113 (`get` method):
```python
resp = self.session.get(url, **kwargs)
# Caller checks status code or calls raise_for_status()
```

Urllib3 retry strategy (lines 41-49) handles transient failures:
```python
retry_strategy = Retry(
    total=retries,
    backoff_factor=backoff,
    status_forcelist=[429, 500, 502, 503, 504],  # Retryable status codes
    allowed_methods=["GET", "POST"],
)
```

**Per-record errors:**
`extractors/propublica.py` lines 52-59:
```python
for i, ein in enumerate(remaining):
    try:
        data = self._fetch_ein(ein)
        if data:
            records.append(data)
    except Exception as e:
        logger.warning(f"Error fetching EIN {ein}: {e}")
    done_eins.add(ein)  # Mark processed even on error
```

Record-level failures don't stop pipeline; progress continues.

**File I/O errors:**
`utils/checkpoint.py` lines 30-37:
```python
try:
    with open(path, "rb") as f:
        data = pickle.load(f)
    logger.info(f"Checkpoint loaded: {name}")
    return data
except (pickle.UnpicklingError, EOFError, OSError) as e:
    logger.warning(f"Failed to load checkpoint {name}: {e}")
    return None
```

Missing or corrupted checkpoint returns None; pipeline restarts that stage.

## Checkpoint System (De-facto Testing via Resumability)

**Location:** `utils/checkpoint.py` (58 lines)

**Purpose:** Enable long-running stages (ProPublica API: 5-8 hours) to resume from last progress point without reprocessing.

**Functions:**

`save_checkpoint(name: str, data) -> Path` (lines 16-22):
- Pickle-serializes data to `data/checkpoints/{name}.pkl`
- Used after every 500 API calls or major stage completion
- Logs size: "Checkpoint saved: {name} ({size:,} bytes)"

`load_checkpoint(name: str)` (lines 25-37):
- Deserializes checkpoint file
- Returns None if file missing (resumability test: handles missing gracefully)
- Catches `pickle.UnpicklingError`, `EOFError`, `OSError` with logged warning
- Resumability test: corrupted checkpoint doesn't crash, stage restarts

`has_checkpoint(name: str) -> bool` (lines 40-41):
- Check before loading: "if resume and has_checkpoint(...)"

`clear_checkpoint(name: str)` and `clear_all_checkpoints()` (lines 44-57):
- Support `--clean` flag to reset all progress
- Logged: "Cleared {count} checkpoint files"

**Testing value:**
Checkpoint cycle validates:
- Serialization round-trip (save → load cycle works)
- Partial progress preservation (state survives checkpoint/reload)
- Resume correctness (deduped EINs don't get re-fetched)

Example in `propublica.py` lines 41-50:
```python
partial = load_checkpoint(f"{self.name}_partial")
if partial is not None:
    records, done_eins = partial  # Checkpoint stored tuple
    self.logger.info(f"Resuming from {len(done_eins):,} completed EINs")
else:
    records = []
    done_eins = set()

remaining = [e for e in self.ein_list if e not in done_eins]  # Skip done
```

## Data Validation (Schema + Coercion)

**Location:** `config/schema.py` (85+ lines)

**Purpose:** Canonical schema defines expected columns, types, and ranges. Coercion standardizes all DataFrames to schema.

**Schema definition** (lines 6-74):
```python
SCHEMA_COLUMNS = [
    ("org_name", "string", "Official organization name"),
    ("ein", "string", "Employer Identification Number (XX-XXXXXXX)"),
    ("total_revenue", "float64", "Total revenue (latest filing)"),
    # ... 45 columns total
]

COLUMN_NAMES = [col[0] for col in SCHEMA_COLUMNS]
COLUMN_DTYPES = {col[0]: col[1] for col in SCHEMA_COLUMNS}
```

**Coercion function** `coerce_schema(df: pd.DataFrame) -> pd.DataFrame`:
- Ensures every DataFrame from extractors/transformers has canonical columns and types
- Called in `BaseExtractor.run()` line 46: `df = coerce_schema(df)`
- Reorders columns to schema order
- Converts dtypes (string → float, etc.)
- Validation: missing columns filled with NaN

**Revenue range bucketing** `revenue_to_range(revenue) -> str`:
- Converts numeric revenue to categorical: "Under $50K", "$50K–$500K", etc.
- Used to bucket organizations for analysis
- Validation: None/invalid values return "Unknown"

## Normalization Functions (Data Validation)

**Location:** `transformers/normalizer.py` (100+ lines)

**Pattern:** Typed return `-> str | None` with validation

Each function validates domain-specific format:

**`normalize_ein(ein) -> str | None`** (lines 14-21):
- Input: any format EIN (with/without dashes, letters, etc.)
- Process: strip non-digits, check length == 9
- Output: XX-XXXXXXX or None if invalid
- Validation: returns None for invalid, not exception

**`normalize_phone(phone) -> str | None`** (lines 24-34):
- Input: any US phone format
- Process: strip non-digits, handle leading 1, check length == 10
- Output: (XXX) XXX-XXXX or None
- Validation: returns None for non-US, wrong length

**`normalize_url(url) -> str | None`** (lines 37-57):
- Input: any URL format (with/without scheme)
- Process: add https:// if missing, parse, rebuild with lowercase domain
- Try-catch: catches urlparse exceptions (malformed URLs)
- Output: https://domain.com or None
- Validation: None for invalid URLs, doesn't crash

**`normalize_state(state) -> str | None`** (lines 60-87):
- Input: state name or 2-letter code
- Process: lookup in state_map dictionary
- Output: 2-letter code or None
- Validation: all 50 states + DC + territories mapped

**`normalize_zip(zipcode) -> str | None`** (lines 90-100):
- Input: any ZIP format
- Process: regex to 5-digit or ZIP+4 (XXXXX or XXXXX-XXXX)
- Output: normalized ZIP or None
- Validation: length check, handles padding

## Integration Testing (via Pipeline Execution)

**How it works:**
Running `python main.py` without flags executes full 8-stage pipeline. Each stage:
1. Depends on previous stage's output (data lineage testing)
2. Produces intermediate parquet (data persistence testing)
3. Logs progress/errors (human validation point)
4. Fails loudly if data contract broken (e.g., missing required columns)

**Key integration test points:**

**Stage 1 → Stage 2 dependency** (`main.py` lines 52-72):
- Stage 1 produces `base_df` (IRS BMF filtered records)
- Stage 2 expects `ein` column to exist
- If missing, ProPublica extraction fails with KeyError (caught and logged)

**Deduplication consistency** (`loaders/deduplicator.py` lines 51-71):
```python
dupes = with_ein.duplicated(subset=["ein"], keep=False)  # Test: detects dupes
unique = with_ein[~dupes]
# Merge duplicates, preserving data
merged = duplicated.groupby("ein", group_keys=False).apply(_merge_rows)
result = pd.concat([unique, merged, without_ein], ignore_index=True)
```

Test assumption: output has no EIN duplicates (validated by next tier)

**CSV output validation** (`loaders/csv_writer.py`):
- Writes final CSV with 50 columns
- Reads back to validate shape, no corrupted data
- Writes summary report with record/column counts (human-readable validation)

## Manual Testing Approach

**Recommended workflow:**

1. **Smoke test** (quick validation):
   ```bash
   python main.py --stages 1 --skip-enrichment  # Download IRS BMF, apply filter
   # Check: data/output/veteran_org_directory.csv exists, has rows
   ```

2. **Data spot-checks**:
   ```python
   import pandas as pd
   df = pd.read_csv("data/output/veteran_org_directory.csv")
   df[df["ein"] == "45-4138378"]  # Expect Active Heroes (EIN from CLAUDE.md)
   df[["org_name", "ein", "state"]].head(20)  # Visual inspection
   ```

3. **API enrichment test** (with small subset):
   ```bash
   # Modify propublica.py to test with first 10 EINs only
   python main.py --stages 2  # Run ProPublica fetch
   # Check: data/intermediate/propublica.parquet has records
   ```

4. **Round-trip validation**:
   ```bash
   python main.py --clean  # Full run from scratch
   # Check: final output vs previous run (row counts, summary stats)
   ```

## Test Coverage Gaps

**Critical untested areas:**

**Web scraping** (`transformers/enricher.py` - Stage 7):
- Scrapes organization websites for social media/email
- No mock sites or test data
- Live URLs required; skipped in most runs (`--skip-enrichment`)
- Risk: broken selectors, timeout behavior not validated

**Charity Navigator API** (`extractors/charity_nav.py`):
- Requires `CHARITY_NAV_API_KEY` env var
- Not configured in default setup (API key missing)
- GraphQL query not tested without live API
- Risk: query syntax errors, response parsing failures unknown

**VA Facilities API** (`extractors/va_facilities.py`):
- Requires `VA_FACILITIES_API_KEY`
- Not configured by default
- Risk: integration failures unknown

**NODC extractor** (`extractors/nodc.py`):
- GitHub CSV URLs have changed (mentioned in CLAUDE.md as broken)
- Not tested; failures expected
- Risk: silent data gaps (broken extractor never called)

**Data enrichment merge logic** (`loaders/merger.py`):
- Multi-source deduplication with priority rules
- No synthetic test data to verify prioritization
- Risk: priority order changes silently break merge

---

*Testing analysis: 2026-02-11*

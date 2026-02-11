# Coding Conventions

**Analysis Date:** 2026-02-11

## Naming Patterns

**Files:**
- `snake_case.py` for all modules and scripts
- Descriptive names aligned with purpose: `base_extractor.py`, `http_client.py`, `deduplicator.py`
- Grouped by domain: extractors, transformers, loaders, utils, config

**Functions:**
- `snake_case` for all function names
- Verb-first naming for primary functions: `extract()`, `transform()`, `run()`, `deduplicate()`, `normalize_*`
- Private helper functions prefixed with single underscore: `_wait_for_rate_limit()`, `_merge_rows()`, `_apply_veteran_filter()`
- Normalization functions follow pattern: `normalize_*()` (e.g., `normalize_ein()`, `normalize_phone()`, `normalize_url()`)

**Variables:**
- `snake_case` throughout
- Constant-like values in `UPPER_CASE` (all caps) for configuration: `IRS_BMF_BASE_URL`, `PROPUBLICA_RATE_LIMIT`, `CHECKPOINT_INTERVAL`
- Dataframe variables clearly named: `base_df`, `combined`, `filtered`, `with_ein`, `without_ein`

**Classes:**
- `PascalCase` for all classes
- Base/abstract classes suffixed with `Base`: `BaseExtractor`
- Extractor subclasses named after source: `IrsBmfExtractor`, `PropublicaExtractor`, `CharityNavExtractor`

## Code Style

**Formatting:**
- Uses `from __future__ import annotations` for forward reference compatibility (Python 3.9+)
- Type hints used throughout with `|` union syntax (requires `from __future__ import annotations`)
- Functions document expected types: `def normalize_ein(ein) -> str | None`
- Class attributes typed: `name: str = "base"` in `BaseExtractor`

**Imports Organization:**
Order observed consistently:
1. `from __future__ import annotations` (if needed, always first)
2. Standard library: `import json`, `import logging`, `import sys`, `from pathlib import Path`
3. Third-party: `import pandas as pd`, `import requests`, `from bs4 import BeautifulSoup`
4. Local imports: `from config.settings import ...`, `from extractors.base_extractor import BaseExtractor`

See examples:
- `app.py` (lines 11-17): stdlib → external → local
- `main.py` (lines 16-23): stdlib → local with multi-line imports
- `http_client.py` (lines 3-13): future → stdlib → external → local

**Long imports:**
Multi-line imports from single module preferred:
```python
from config.settings import (
    IRS_BMF_BASE_URL,
    IRS_BMF_FILES,
    RAW_DIR,
)
```

## Error Handling

**Pattern: Try-except with specific exception types**

Caught specific exceptions, never bare `except:`:
- `pickle.UnpicklingError`, `EOFError`, `OSError` in `utils/checkpoint.py`
- `json.JSONDecodeError`, `OSError` in `utils/http_client.py`
- HTTP status codes checked explicitly: `if resp.status_code == 404:` in `extractors/propublica.py`
- `resp.raise_for_status()` used for non-404 errors

Graceful degradation pattern:
```python
try:
    data = parse_complex_data()
except SpecificError as e:
    logger.warning(f"Error parsing: {e}")
    return None  # or default value
```

See `utils/http_client.py` lines 74-78 (JSON decode), `transformers/normalizer.py` lines 49-57 (URL parsing).

**Error logging:**
- Use logger at appropriate level: `logger.warning()` for expected failures, `logger.error()` for unexpected
- Always include context: `logger.warning(f"Error fetching EIN {ein}: {e}")`
- Logger setup: each module gets named logger with `logging.getLogger(__name__)`

## Logging

**Framework:** Python standard `logging` module

**Logger initialization:**
```python
logger = logging.getLogger(__name__)
```

Used in every module that logs. Logger names become module paths (e.g., `extractor.irs_bmf`, `http_client`).

**Log setup in main entrypoint:**
`main.py` lines 28-37 configure:
- Level from env var `LOG_LEVEL` (default: INFO)
- Format: `"%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s"`
- Handlers: stdout + file to `data/output/pipeline.log`

**When to log:**
- `logger.info()` for major transitions: "Starting extraction", "Completed stage X"
- `logger.info()` with counts/metrics: `f"Extracted {len(df):,} records"`
- `logger.warning()` for recoverable issues: failed API calls, skipped records
- `logger.debug()` for fine-grained progress (sparingly used)

## Comments

**When to Comment:**
- Module docstrings (triple-quoted) at top of every file: describe purpose, usage if applicable
- Function docstrings: one-liner or multi-line describing purpose and return type
- Inline comments rare; code clarity preferred over comments

**Docstring style:**
Short docstrings for simple functions:
```python
def normalize_ein(ein) -> str | None:
    """Normalize EIN to XX-XXXXXXX format."""
```

Multi-line for complex functions with context:
```python
def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Run all three dedup tiers in sequence."""
```

Module-level docstrings provide overview:
```python
"""IRS Exempt Organizations Business Master File (BMF) extractor.

Downloads eo1–eo4.csv from IRS SOI, applies three-tier veteran org filter:
  1. NTEE W-prefix codes (military/veterans)
  2. 501(c)(19) subsection (armed forces orgs)
  3. Keyword match on org names
"""
```

**No JSDoc/TypeDoc:** Uses Python type hints instead of special comment blocks.

## Function Design

**Size:** Functions keep to single responsibility. Examples:
- `_wait_for_rate_limit()` in `RateLimitedSession`: just rate limiting logic
- `_cache_key()`: hashing only
- `normalize_*()` functions: single field normalization

**Parameters:**
- Keyword-argument defaults common: `def get(self, url: str, use_cache: bool = True, **kwargs)`
- Complex configs passed as objects from `config/settings.py`: `PROPUBLICA_RATE_LIMIT`, `DEFAULT_TIMEOUT`
- Optional parameters with `| None` type hint: `ein_list: list[str] | None = None`

**Return Values:**
- Return early pattern for validation:
  ```python
  if pd.isna(ein) or ein is None:
      return None
  ```
- Functions return typed values: `-> str | None`, `-> pd.DataFrame`, `-> dict | None`
- None used for missing/invalid data (not exceptions)

## Module Design

**Exports:**
- Classes exported at module level: `class BaseExtractor(ABC):`
- Functions exported at module level: `def deduplicate(df: pd.DataFrame)`
- No explicit `__all__` declarations observed; all top-level definitions are importable

**Barrel Files:**
- Minimal `__init__.py` usage observed
- `config/__init__.py`, `extractors/__init__.py` exist but empty
- Direct imports preferred: `from extractors.irs_bmf import IrsBmfExtractor` not `from extractors import IrsBmfExtractor`

**Architectural Patterns:**

**Base Class Pattern:**
`BaseExtractor` (lines 16-66 in `extractors/base_extractor.py`) defines:
- Abstract `extract()` method
- Template method `run()` orchestrating extract → transform → schema coercion → checkpoint
- Subclasses override `extract()` and optionally `transform()`

**Service Class Pattern:**
`RateLimitedSession` (lines 25-131 in `utils/http_client.py`) wraps HTTP concerns:
- Rate limiting via `_wait_for_rate_limit()`
- Disk caching via `_cache_key()`, `_get_cached()`, `_set_cached()`
- Retry logic via urllib3 HTTPAdapter
- Exposed methods: `get()`, `post()`, `download_file()`

**Checkpoint Pattern:**
Functions in `utils/checkpoint.py` provide resumability for long stages:
- `save_checkpoint(name, data)`: pickle to disk
- `load_checkpoint(name)`: load with error recovery
- `has_checkpoint(name)`: check existence
- Used in extractors: `load_checkpoint(f"{self.name}_partial")` for partial progress

## Data Flow Conventions

**DataFrame manipulation:**
- Consistent column naming: lowercase with underscores (`org_name`, `ein`, `total_revenue`)
- Chain operations where possible: `df.columns = df.columns.str.strip().str.upper()`
- Use `.copy()` when modifying subset: `group_copy = group.iloc[0].copy()`
- Mask-based filtering: `mask = df["status"].isin(values)` then `df[mask]`

**Null handling:**
- Check with `pd.isna()` not `is None` for Series/columns
- Use `.dropna()` to filter: `df["field"].dropna().unique()`
- Use `.fillna()` for defaults: `df["sources"].fillna("")`
- None returned from functions for missing data, not `pd.NA`

---

*Convention analysis: 2026-02-11*

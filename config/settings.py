"""Global settings: URLs, paths, rate limits, API key references."""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Paths ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INTERMEDIATE_DIR = DATA_DIR / "intermediate"
OUTPUT_DIR = DATA_DIR / "output"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"

for d in (RAW_DIR, INTERMEDIATE_DIR, OUTPUT_DIR, CHECKPOINT_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ── IRS BMF ────────────────────────────────────────────────────────────
IRS_BMF_BASE_URL = "https://www.irs.gov/pub/irs-soi"
IRS_BMF_FILES = ["eo1.csv", "eo2.csv", "eo3.csv", "eo4.csv"]

# ── ProPublica Nonprofit Explorer ──────────────────────────────────────
PROPUBLICA_BASE_URL = "https://projects.propublica.org/nonprofits/api/v2"
PROPUBLICA_RATE_LIMIT = 2.0  # requests per second

# ── Charity Navigator ──────────────────────────────────────────────────
CHARITY_NAV_GRAPHQL_URL = "https://api.charitynavigator.org/graphql"
CHARITY_NAV_API_KEY = os.getenv("CHARITY_NAVIGATOR_API_KEY", "")
CHARITY_NAV_RATE_LIMIT = 1.0  # requests per second

# ── VA Lighthouse Facilities API ───────────────────────────────────────
VA_FACILITIES_BASE_URL = "https://api.va.gov/services/va_facilities/v1/facilities"
VA_FACILITIES_API_KEY = os.getenv("VA_FACILITIES_API_KEY", "")
VA_FACILITIES_RATE_LIMIT = 5.0

# ── VA OGC VSO Directory ──────────────────────────────────────────────
VA_VSO_SEARCH_URL = "https://www.va.gov/ogc/apps/accreditation/index.asp"

# ── National Resource Directory ────────────────────────────────────────
NRD_BASE_URL = "https://www.nrd.gov"
NRD_RATE_LIMIT = 0.5  # requests per second

# ── NODC (Nonprofit Open Data Collective) ─────────────────────────────
NODC_GITHUB_BASE = "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file/master"

# ── HTTP defaults ──────────────────────────────────────────────────────
DEFAULT_TIMEOUT = 30  # seconds
DEFAULT_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 1.0  # seconds, multiplied by attempt number
DISK_CACHE_DIR = DATA_DIR / "http_cache"
DISK_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ── Checkpoint settings ────────────────────────────────────────────────
CHECKPOINT_INTERVAL = 500  # save every N API calls

# ── Enricher (web scraping for social media) ───────────────────────────
ENRICHER_RATE_LIMIT = 0.5  # requests per second
ENRICHER_TIMEOUT = 15

# ── Logging ────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

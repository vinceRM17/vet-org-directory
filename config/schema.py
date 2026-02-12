"""Canonical 45-column DataFrame schema for the veteran org directory."""

import pandas as pd

# Column definitions: (column_name, dtype, description)
SCHEMA_COLUMNS = [
    # Identity
    ("org_name", "string", "Official organization name"),
    ("org_name_alt", "string", "Alternate / DBA name"),
    ("ein", "string", "Employer Identification Number (XX-XXXXXXX)"),
    ("org_type", "string", "Organization type (501c3, 501c19, etc.)"),

    # Contact
    ("street_address", "string", "Primary street address"),
    ("street_address_2", "string", "Suite / unit / PO Box"),
    ("city", "string", "City"),
    ("state", "string", "Two-letter state code"),
    ("zip_code", "string", "ZIP or ZIP+4"),
    ("country", "string", "Country code (US default)"),
    ("phone", "string", "Primary phone number"),
    ("email", "string", "Primary email address"),
    ("website", "string", "Organization website URL"),

    # Classification
    ("ntee_code", "string", "NTEE classification code"),
    ("ntee_description", "string", "NTEE classification description"),
    ("irs_subsection", "string", "IRS subsection code (e.g. 03, 19)"),
    ("irs_filing_requirement", "string", "IRS filing requirement code"),
    ("tax_exempt_status", "string", "Tax-exempt status description"),
    ("ruling_date", "string", "Date tax-exempt status was granted"),

    # Description
    ("mission_statement", "string", "Organization mission statement"),
    ("services_offered", "string", "Description of services offered"),
    ("service_categories", "string", "Semicolon-separated service categories"),
    ("eligibility_requirements", "string", "Who is eligible for services"),
    ("service_area", "string", "Geographic service area"),
    ("year_founded", "string", "Year organization was founded"),

    # Financials
    ("fiscal_year_end", "string", "Fiscal year end month (MM)"),
    ("total_revenue", "float64", "Total revenue (latest filing)"),
    ("total_expenses", "float64", "Total expenses (latest filing)"),
    ("total_assets", "float64", "Total assets (latest filing)"),
    ("total_liabilities", "float64", "Total liabilities (latest filing)"),
    ("net_assets", "float64", "Net assets (latest filing)"),
    ("annual_revenue_range", "string", "Revenue range bucket"),

    # Organizational
    ("num_employees", "float64", "Number of employees"),
    ("num_volunteers", "float64", "Number of volunteers"),
    ("key_personnel", "string", "JSON array of key personnel"),
    ("board_members", "string", "Semicolon-separated board members"),

    # Ratings
    ("charity_navigator_rating", "float64", "Charity Navigator star rating (0-4)"),
    ("charity_navigator_score", "float64", "Charity Navigator overall score (0-100)"),
    ("cn_alert_level", "string", "Charity Navigator advisory/alert level"),
    ("va_accredited", "string", "VA accreditation status (Yes/No)"),
    ("accreditation_details", "string", "Details of VA accreditation"),

    # Social Media
    ("facebook_url", "string", "Facebook page URL"),
    ("twitter_url", "string", "Twitter/X profile URL"),
    ("linkedin_url", "string", "LinkedIn page URL"),
    ("instagram_url", "string", "Instagram profile URL"),
    ("youtube_url", "string", "YouTube channel URL"),

    # Metadata
    ("data_sources", "string", "Semicolon-separated list of data sources"),
    ("data_freshness_date", "string", "Date data was last collected (YYYY-MM-DD)"),
    ("confidence_score", "float64", "Record completeness score (0.0 - 1.0)"),
    ("confidence_grade", "string", "Letter grade A-F based on data completeness"),
    ("confidence_detail", "string", "JSON with per-group filled/total/source breakdown"),
    ("record_last_updated", "string", "Timestamp of last update"),
]

COLUMN_NAMES = [col[0] for col in SCHEMA_COLUMNS]
COLUMN_DTYPES = {col[0]: col[1] for col in SCHEMA_COLUMNS}


def empty_dataframe() -> pd.DataFrame:
    """Return an empty DataFrame with the canonical schema."""
    df = pd.DataFrame(columns=COLUMN_NAMES)
    for col, dtype, _ in SCHEMA_COLUMNS:
        if dtype == "float64":
            df[col] = pd.array([], dtype="Float64")
        else:
            df[col] = pd.array([], dtype="string")
    return df


def coerce_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a DataFrame to the canonical schema, adding missing columns."""
    for col, dtype, _ in SCHEMA_COLUMNS:
        if col not in df.columns:
            if dtype == "float64":
                df[col] = pd.array([pd.NA] * len(df), dtype="Float64")
            else:
                df[col] = pd.array([pd.NA] * len(df), dtype="string")
        else:
            if dtype == "float64":
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
            else:
                df[col] = df[col].astype("string")
    return df[COLUMN_NAMES]


# Revenue range buckets
REVENUE_RANGES = [
    (0, 0, "$0"),
    (1, 49_999, "Under $50K"),
    (50_000, 99_999, "$50K–$100K"),
    (100_000, 499_999, "$100K–$500K"),
    (500_000, 999_999, "$500K–$1M"),
    (1_000_000, 4_999_999, "$1M–$5M"),
    (5_000_000, 9_999_999, "$5M–$10M"),
    (10_000_000, 49_999_999, "$10M–$50M"),
    (50_000_000, 99_999_999, "$50M–$100M"),
    (100_000_000, float("inf"), "$100M+"),
]


def revenue_to_range(revenue) -> str:
    """Convert a revenue number to a human-readable range bucket."""
    if pd.isna(revenue) or revenue is None:
        return pd.NA
    revenue = float(revenue)
    for low, high, label in REVENUE_RANGES:
        if low <= revenue <= high:
            return label
    return pd.NA


# Confidence score weights (sum = 1.0)
CONFIDENCE_WEIGHTS = {
    "org_name": 0.10,
    "ein": 0.08,
    "street_address": 0.06,
    "city": 0.05,
    "state": 0.05,
    "zip_code": 0.04,
    "phone": 0.06,
    "email": 0.06,
    "website": 0.06,
    "ntee_code": 0.04,
    "mission_statement": 0.05,
    "total_revenue": 0.05,
    "total_assets": 0.04,
    "num_employees": 0.03,
    "charity_navigator_rating": 0.04,
    "va_accredited": 0.03,
    "services_offered": 0.04,
    "facebook_url": 0.02,
    "twitter_url": 0.02,
    "data_sources": 0.04,
    "key_personnel": 0.04,
}


# ── Field Groups (for per-group confidence breakdown) ────────────────
FIELD_GROUPS = {
    "identity": {
        "label": "Identity",
        "icon": "🏢",
        "fields": ["org_name", "ein", "org_type"],
        "source_hint": "irs_bmf",
    },
    "location": {
        "label": "Location",
        "icon": "📍",
        "fields": ["street_address", "city", "state", "zip_code"],
        "source_hint": "irs_bmf",
    },
    "classification": {
        "label": "Classification",
        "icon": "📋",
        "fields": ["ntee_code", "irs_subsection", "tax_exempt_status"],
        "source_hint": "irs_bmf",
    },
    "financials": {
        "label": "Financials",
        "icon": "💰",
        "fields": ["total_revenue", "total_expenses", "total_assets", "net_assets"],
        "source_hint": "propublica",
    },
    "contact": {
        "label": "Contact",
        "icon": "📞",
        "fields": ["phone", "email", "website"],
        "source_hint": "web_enrichment",
    },
    "ratings": {
        "label": "Ratings",
        "icon": "⭐",
        "fields": ["charity_navigator_rating", "va_accredited"],
        "source_hint": "charity_nav / va_vso",
    },
    "description": {
        "label": "Description",
        "icon": "📝",
        "fields": ["mission_statement", "services_offered", "service_categories"],
        "source_hint": "nrd / web_enrichment",
    },
    "social": {
        "label": "Social Media",
        "icon": "🌐",
        "fields": ["facebook_url", "twitter_url", "linkedin_url", "instagram_url"],
        "source_hint": "web_enrichment",
    },
    "personnel": {
        "label": "Personnel",
        "icon": "👥",
        "fields": ["key_personnel", "board_members"],
        "source_hint": "propublica / nrd",
    },
}


# ── Confidence Grade Criteria (rule-based, checked top-down) ────────
#
# A (Verified):  Has identity + financials + at least 1 contact + rating/VA
# B (Strong):    Has identity + financials + NTEE classification
# C (Basic):     Has identity + (financials OR NTEE classification)
# D (Minimal):   Has identity fields (name + EIN + address)
# F (Stub):      Missing EIN or address
#
CONFIDENCE_TIERS = [
    {
        "grade": "A", "label": "Verified", "color": "#2F855A",
        "description": "Identity + financials + contact + rating/VA accreditation",
    },
    {
        "grade": "B", "label": "Strong", "color": "#2C5282",
        "description": "Identity + financials + NTEE classification",
    },
    {
        "grade": "C", "label": "Basic", "color": "#D69E2E",
        "description": "Identity + financials or NTEE classification",
    },
    {
        "grade": "D", "label": "Minimal", "color": "#DD6B20",
        "description": "Identity fields only (name + EIN + address)",
    },
    {
        "grade": "F", "label": "Stub", "color": "#C53030",
        "description": "Missing EIN or address",
    },
]

GRADE_INFO = {t["grade"]: t for t in CONFIDENCE_TIERS}
GRADE_OPTIONS = [f"{t['grade']} - {t['label']}" for t in CONFIDENCE_TIERS]

"""Data normalization for EINs, phone numbers, URLs, addresses, and org names."""

from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

import pandas as pd

logger = logging.getLogger(__name__)


def normalize_ein(ein) -> str | None:
    """Normalize EIN to XX-XXXXXXX format."""
    if pd.isna(ein) or ein is None:
        return None
    ein = re.sub(r"[^0-9]", "", str(ein))
    if len(ein) != 9:
        return None
    return f"{ein[:2]}-{ein[2:]}"


def normalize_phone(phone) -> str | None:
    """Normalize US phone number to (XXX) XXX-XXXX format."""
    if pd.isna(phone) or phone is None:
        return None
    digits = re.sub(r"[^0-9]", "", str(phone))
    # Strip leading 1 for US numbers
    if len(digits) == 11 and digits[0] == "1":
        digits = digits[1:]
    if len(digits) != 10:
        return None
    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def normalize_url(url) -> str | None:
    """Normalize URL: ensure scheme, lowercase domain, strip trailing slash."""
    if pd.isna(url) or url is None:
        return None
    url = str(url).strip()
    if not url:
        return None

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        parsed = urlparse(url)
        if not parsed.netloc:
            return None
        # Rebuild with lowercase domain
        normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}"
        return normalized.rstrip("/")
    except Exception:
        return None


def normalize_state(state) -> str | None:
    """Normalize state to 2-letter uppercase code."""
    if pd.isna(state) or state is None:
        return None
    state = str(state).strip().upper()
    if len(state) == 2:
        return state

    # Common full names → abbreviations
    state_map = {
        "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
        "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
        "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
        "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
        "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
        "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN",
        "MISSISSIPPI": "MS", "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE",
        "NEVADA": "NV", "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ",
        "NEW MEXICO": "NM", "NEW YORK": "NY", "NORTH CAROLINA": "NC",
        "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK", "OREGON": "OR",
        "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
        "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
        "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA",
        "WEST VIRGINIA": "WV", "WISCONSIN": "WI", "WYOMING": "WY",
        "DISTRICT OF COLUMBIA": "DC", "PUERTO RICO": "PR",
        "VIRGIN ISLANDS": "VI", "GUAM": "GU", "AMERICAN SAMOA": "AS",
    }
    return state_map.get(state, state if len(state) == 2 else None)


def normalize_zip(zipcode) -> str | None:
    """Normalize ZIP code to 5-digit or ZIP+4 format."""
    if pd.isna(zipcode) or zipcode is None:
        return None
    z = re.sub(r"[^0-9-]", "", str(zipcode))
    # Strip trailing zeros that are clearly padding
    if len(z) >= 5:
        base = z[:5]
        if len(z) > 5:
            ext = z[5:].lstrip("-")
            if ext and len(ext) == 4:
                return f"{base}-{ext}"
        return base
    return None


def normalize_org_name(name) -> str | None:
    """Standardize org name: title case, clean whitespace, expand common abbrevs."""
    if pd.isna(name) or name is None:
        return None
    name = str(name).strip()
    if not name:
        return None

    # Collapse multiple spaces
    name = re.sub(r"\s+", " ", name)

    # Title case, preserving known acronyms
    acronyms = {"VFW", "DAV", "AMVETS", "USO", "VA", "USA", "US", "PTSD", "POW", "MIA"}
    words = name.title().split()
    result = []
    for w in words:
        if w.upper() in acronyms:
            result.append(w.upper())
        else:
            result.append(w)

    return " ".join(result)


def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Apply all normalizations to a DataFrame in-place."""
    logger.info(f"Normalizing {len(df):,} records")

    if "ein" in df.columns:
        df["ein"] = df["ein"].apply(normalize_ein)

    if "phone" in df.columns:
        df["phone"] = df["phone"].apply(normalize_phone)

    if "website" in df.columns:
        df["website"] = df["website"].apply(normalize_url)

    if "state" in df.columns:
        df["state"] = df["state"].apply(normalize_state)

    if "zip_code" in df.columns:
        df["zip_code"] = df["zip_code"].apply(normalize_zip)

    if "org_name" in df.columns:
        df["org_name"] = df["org_name"].apply(normalize_org_name)

    for url_col in ["facebook_url", "twitter_url", "linkedin_url", "instagram_url", "youtube_url"]:
        if url_col in df.columns:
            df[url_col] = df[url_col].apply(normalize_url)

    if "email" in df.columns:
        df["email"] = df["email"].str.strip().str.lower()

    if "country" in df.columns:
        df["country"] = df["country"].fillna("US")
    else:
        df["country"] = "US"

    logger.info("Normalization complete")
    return df

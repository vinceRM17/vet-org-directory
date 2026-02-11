"""IRS Exempt Organizations Business Master File (BMF) extractor.

Downloads eo1–eo4.csv from IRS SOI, applies three-tier veteran org filter:
  1. NTEE W-prefix codes (military/veterans)
  2. 501(c)(19) subsection (armed forces orgs)
  3. Keyword match on org names
"""

import logging
import re

import pandas as pd

from config.ntee_codes import EXCLUDE_PATTERNS, VETERAN_KEYWORDS
from config.settings import IRS_BMF_BASE_URL, IRS_BMF_FILES, RAW_DIR
from extractors.base_extractor import BaseExtractor
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

# IRS BMF column names (these CSVs have headers)
BMF_USECOLS = [
    "EIN", "NAME", "ICO", "STREET", "CITY", "STATE", "ZIP",
    "GROUP", "SUBSECTION", "AFFILIATION", "CLASSIFICATION",
    "RULING", "DEDUCTIBILITY", "FOUNDATION", "ACTIVITY",
    "ORGANIZATION", "STATUS", "TAX_PERIOD", "ASSET_CD",
    "INCOME_CD", "FILING_REQ_CD", "PF_FILING_REQ_CD",
    "ACCT_PD", "ASSET_AMT", "INCOME_AMT", "REVENUE_AMT",
    "NTEE_CD", "SORT_NAME",
]


class IrsBmfExtractor(BaseExtractor):
    name = "irs_bmf"

    def __init__(self):
        super().__init__()
        self.http = RateLimitedSession(rate_limit=1.0)

    def extract(self) -> pd.DataFrame:
        frames = []
        for filename in IRS_BMF_FILES:
            url = f"{IRS_BMF_BASE_URL}/{filename}"
            dest = RAW_DIR / filename
            if not dest.exists():
                self.http.download_file(url, dest)
            else:
                self.logger.info(f"Using cached {dest}")

            df = pd.read_csv(
                dest,
                dtype=str,
                low_memory=False,
                encoding="latin-1",
            )
            # Normalize column names to upper
            df.columns = df.columns.str.strip().str.upper()
            frames.append(df)
            self.logger.info(f"Loaded {filename}: {len(df):,} rows")

        combined = pd.concat(frames, ignore_index=True)
        self.logger.info(f"Total BMF records: {len(combined):,}")

        filtered = self._apply_veteran_filter(combined)
        self.logger.info(f"Veteran-filtered records: {len(filtered):,}")
        return filtered

    def _apply_veteran_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        # Tier 1: NTEE W-prefix
        ntee_mask = df["NTEE_CD"].str.startswith("W", na=False)
        self.logger.info(f"  NTEE W-prefix matches: {ntee_mask.sum():,}")

        # Tier 2: 501(c)(19) subsection
        subsection_mask = df["SUBSECTION"].str.strip() == "19"
        self.logger.info(f"  501(c)(19) matches: {subsection_mask.sum():,}")

        # Tier 3: Keyword match on NAME
        keyword_mask = self._keyword_match(df["NAME"])
        self.logger.info(f"  Keyword name matches: {keyword_mask.sum():,}")

        combined_mask = ntee_mask | subsection_mask | keyword_mask
        result = df[combined_mask].copy()

        # Remove false positives
        exclude_mask = self._exclude_match(result["NAME"])
        if exclude_mask.any():
            self.logger.info(f"  Excluding {exclude_mask.sum():,} false positives")
            result = result[~exclude_mask]

        return result.drop_duplicates(subset=["EIN"])

    def _keyword_match(self, names: pd.Series) -> pd.Series:
        lower_names = names.str.lower().fillna("")
        pattern = "|".join(re.escape(kw) for kw in VETERAN_KEYWORDS)
        return lower_names.str.contains(pattern, regex=True, na=False)

    def _exclude_match(self, names: pd.Series) -> pd.Series:
        lower_names = names.str.lower().fillna("")
        pattern = "|".join(re.escape(kw) for kw in EXCLUDE_PATTERNS)
        return lower_names.str.contains(pattern, regex=True, na=False)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = pd.DataFrame()
        out["org_name"] = df["NAME"].str.strip().str.title()
        out["org_name_alt"] = df.get("SORT_NAME", pd.Series(dtype="string")).str.strip().str.title()
        out["ein"] = df["EIN"].str.strip()
        out["street_address"] = df["STREET"].str.strip().str.title()
        out["city"] = df["CITY"].str.strip().str.title()
        out["state"] = df["STATE"].str.strip().str.upper()
        out["zip_code"] = df["ZIP"].str.strip().str[:10]
        out["country"] = "US"
        out["ntee_code"] = df["NTEE_CD"].str.strip()
        out["irs_subsection"] = df["SUBSECTION"].str.strip()
        out["irs_filing_requirement"] = df["FILING_REQ_CD"].str.strip()
        out["ruling_date"] = df["RULING"].str.strip()
        out["fiscal_year_end"] = df["ACCT_PD"].str.strip()
        out["total_assets"] = pd.to_numeric(df["ASSET_AMT"], errors="coerce")
        out["total_revenue"] = pd.to_numeric(df["REVENUE_AMT"], errors="coerce")

        # Derive org_type from subsection
        subsection_map = {
            "03": "501(c)(3)",
            "04": "501(c)(4)",
            "19": "501(c)(19)",
            "23": "501(c)(23)",
        }
        out["org_type"] = df["SUBSECTION"].str.strip().map(subsection_map).fillna(
            "501(c)(" + df["SUBSECTION"].str.strip() + ")"
        )

        # Derive tax_exempt_status from STATUS
        status_map = {
            "01": "Unconditional Exemption",
            "02": "Conditional Exemption",
            "12": "Trust described in section 4947(a)(2)",
            "25": "Organization terminated",
        }
        out["tax_exempt_status"] = df.get("STATUS", pd.Series(dtype="string"))
        if "STATUS" in df.columns:
            out["tax_exempt_status"] = df["STATUS"].str.strip().map(status_map)

        return out

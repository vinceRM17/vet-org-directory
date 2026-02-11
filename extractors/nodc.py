"""Nonprofit Open Data Collective (NODC) extractor.

Downloads the master concordance file and IRS 990 e-file data from GitHub
to enrich our directory with mission statements, program descriptions,
and employee/volunteer counts.
"""

from __future__ import annotations

import logging

import pandas as pd

from config.settings import RAW_DIR
from extractors.base_extractor import BaseExtractor
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

# Corrected NODC GitHub URLs (file was renamed from efiler_master_concordance.csv)
NODC_BASE = "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file/master"
CONCORDANCE_URL = f"{NODC_BASE}/concordance.csv"

# Additional NODC data repos
NODC_BMF_REPO = "https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-exempt-org-business-master-file/master"


class NodcExtractor(BaseExtractor):
    name = "nodc"

    def __init__(self, ein_list: list[str] | None = None):
        super().__init__()
        self.ein_list = set(ein_list or [])
        self.http = RateLimitedSession(rate_limit=2.0, cache_name="nodc")

    def extract(self) -> pd.DataFrame:
        """Download NODC data and filter to our EIN list."""
        # Download the concordance file (field mappings for 990 forms)
        concordance_path = RAW_DIR / "nodc_concordance.csv"
        if not concordance_path.exists():
            try:
                self.http.download_file(CONCORDANCE_URL, concordance_path)
                self.logger.info("Downloaded NODC concordance file")
            except Exception as e:
                self.logger.warning(f"Could not download NODC concordance: {e}")

        # Try multiple data file locations
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

                df = pd.read_csv(dest, dtype=str, low_memory=False)
                df.columns = df.columns.str.strip().str.upper()

                # Filter to our EIN list
                ein_col = self._find_ein_column(df)
                if ein_col and self.ein_list:
                    # Normalize EINs for matching (strip hyphens)
                    df["_ein_clean"] = df[ein_col].str.replace("-", "", regex=False).str.strip()
                    clean_eins = {e.replace("-", "").strip() for e in self.ein_list}
                    df = df[df["_ein_clean"].isin(clean_eins)]
                    df.drop(columns=["_ein_clean"], inplace=True)
                    self.logger.info(f"NODC filtered to {len(df):,} matching records from {url}")

                if len(df) > 0:
                    return df

            except Exception as e:
                self.logger.warning(f"Could not process NODC file {url}: {e}")
                continue

        self.logger.info("No NODC data files yielded results")
        return pd.DataFrame()

    def _find_ein_column(self, df: pd.DataFrame) -> str | None:
        for candidate in ["EIN", "TAXPAYER_ID", "ORG_EIN", "FEIN"]:
            if candidate in df.columns:
                return candidate
        return None

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df

        out = pd.DataFrame()

        col_map = {
            "EIN": "ein",
            "TAXPAYER_ID": "ein",
            "ORG_EIN": "ein",
            "FEIN": "ein",
            "ORG_NAME": "org_name",
            "NAME": "org_name",
            "MISSION": "mission_statement",
            "MISSION_DESCRIPTION": "mission_statement",
            "MISSION_DESC": "mission_statement",
            "PROGRAM_SERVICE_DESC": "services_offered",
            "PROGRAM_DESCRIPTION": "services_offered",
            "NUM_EMPLOYEES": "num_employees",
            "EMPLOYEECNT": "num_employees",
            "NUM_VOLUNTEERS": "num_volunteers",
            "VOLUNTEERCNT": "num_volunteers",
            "TOTAL_REVENUE": "total_revenue",
            "TOTREVENUE": "total_revenue",
            "TOTAL_EXPENSES": "total_expenses",
            "TOTFUNCEXPNS": "total_expenses",
            "TOTAL_ASSETS": "total_assets",
            "TOTASSETSEND": "total_assets",
            "WEBSITE": "website",
            "WEBURL": "website",
        }

        for src_col, dest_col in col_map.items():
            if src_col in df.columns and dest_col not in out.columns:
                out[dest_col] = df[src_col]

        return out

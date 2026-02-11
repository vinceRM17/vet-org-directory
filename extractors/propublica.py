"""ProPublica Nonprofit Explorer API enrichment extractor.

For each EIN, fetches organization details and latest filing financials.
Checkpoints every 500 EINs for resumability.
"""

from __future__ import annotations

import json
import logging
import time

import pandas as pd

from config.settings import (
    CHECKPOINT_INTERVAL,
    PROPUBLICA_BASE_URL,
    PROPUBLICA_RATE_LIMIT,
)
from extractors.base_extractor import BaseExtractor
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)


class PropublicaExtractor(BaseExtractor):
    name = "propublica"

    def __init__(self, ein_list: list[str] | None = None):
        super().__init__()
        self.ein_list = ein_list or []
        self.http = RateLimitedSession(
            rate_limit=PROPUBLICA_RATE_LIMIT,
            cache_name="propublica",
        )

    def extract(self) -> pd.DataFrame:
        """Fetch org details from ProPublica for each EIN."""
        # Check for partial progress
        partial = load_checkpoint(f"{self.name}_partial")
        if partial is not None:
            records, done_eins = partial
            self.logger.info(f"Resuming from {len(done_eins):,} completed EINs")
        else:
            records = []
            done_eins = set()

        remaining = [e for e in self.ein_list if e not in done_eins]
        self.logger.info(f"Fetching {len(remaining):,} EINs from ProPublica")

        for i, ein in enumerate(remaining):
            try:
                data = self._fetch_ein(ein)
                if data:
                    records.append(data)
            except Exception as e:
                self.logger.warning(f"Error fetching EIN {ein}: {e}")

            done_eins.add(ein)

            if (i + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(f"{self.name}_partial", (records, done_eins))
                self.logger.info(
                    f"ProPublica progress: {len(done_eins):,}/{len(self.ein_list):,}"
                )

        return pd.DataFrame(records) if records else pd.DataFrame()

    def _fetch_ein(self, ein: str) -> dict | None:
        url = f"{PROPUBLICA_BASE_URL}/organizations/{ein}.json"
        resp = self.http.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()

        data = resp.json()
        org = data.get("organization", {})
        filings = data.get("filings_with_data", [])
        latest = filings[0] if filings else {}

        return {
            "ein": ein,
            "pp_name": org.get("name"),
            "pp_city": org.get("city"),
            "pp_state": org.get("state"),
            "pp_ntee": org.get("ntee_code"),
            "num_employees": org.get("number_of_forms_filed"),
            "total_revenue": latest.get("totrevenue"),
            "total_expenses": latest.get("totfuncexpns"),
            "total_assets": latest.get("totassetsend"),
            "total_liabilities": latest.get("totliabend"),
            "net_assets": latest.get("totnetassetend"),
            "fiscal_year_end": latest.get("tax_prd"),
            "key_personnel": self._extract_officers(latest),
        }

    def _extract_officers(self, filing: dict) -> str | None:
        officers = filing.get("officers", [])
        if not officers:
            return None
        personnel = []
        for o in officers[:10]:  # Limit to top 10
            personnel.append({
                "name": o.get("name", ""),
                "title": o.get("title", ""),
                "compensation": o.get("compensation"),
            })
        return json.dumps(personnel)

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = pd.DataFrame()
        out["ein"] = df["ein"]
        out["num_employees"] = pd.to_numeric(df.get("num_employees"), errors="coerce")
        out["total_revenue"] = pd.to_numeric(df.get("total_revenue"), errors="coerce")
        out["total_expenses"] = pd.to_numeric(df.get("total_expenses"), errors="coerce")
        out["total_assets"] = pd.to_numeric(df.get("total_assets"), errors="coerce")
        out["total_liabilities"] = pd.to_numeric(df.get("total_liabilities"), errors="coerce")
        out["net_assets"] = pd.to_numeric(df.get("net_assets"), errors="coerce")
        out["key_personnel"] = df.get("key_personnel")
        return out

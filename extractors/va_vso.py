"""VA OGC VSO Accreditation Directory extractor.

Uses the VA OGC Excel dump endpoints to get complete lists of
accredited VSOs and their representatives.
"""

from __future__ import annotations

import json
import logging

import pandas as pd
from bs4 import BeautifulSoup

from extractors.base_extractor import BaseExtractor
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

# Direct HTML-table dump URLs (return complete datasets)
VSO_ORGS_URL = "https://www.va.gov/ogc/apps/accreditation/orgsexcellist.asp"
VSO_REPS_URL = "https://www.va.gov/ogc/apps/accreditation/repexcellist.asp"
VSO_SEARCH_URL = "https://www.va.gov/ogc/apps/accreditation/accredvso.asp"


class VaVsoExtractor(BaseExtractor):
    name = "va_vso"

    def __init__(self):
        super().__init__()
        self.http = RateLimitedSession(rate_limit=0.5, cache_name="va_vso")

    def extract(self) -> pd.DataFrame:
        # Try the Excel dump endpoints first (most complete)
        org_records = self._fetch_orgs_excel()
        if org_records:
            self.logger.info(f"VA VSO orgs Excel dump: {len(org_records)} records")
            return pd.DataFrame(org_records)

        # Fallback: POST to search with blank fields to get all orgs
        self.logger.info("Excel dump failed, trying POST search fallback")
        fallback_records = self._fetch_via_search()
        if fallback_records:
            self.logger.info(f"VA VSO search fallback: {len(fallback_records)} records")
            return pd.DataFrame(fallback_records)

        return pd.DataFrame()

    def _fetch_orgs_excel(self) -> list[dict]:
        """Fetch the complete VSO org+rep Excel dump (HTML table)."""
        records = []
        try:
            resp = self.http.get(VSO_ORGS_URL, use_cache=False)
            if resp.status_code != 200:
                self.logger.warning(f"VSO orgs Excel dump returned {resp.status_code}")
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            table = soup.find("table")
            if not table:
                self.logger.warning("No table found in VSO orgs Excel dump")
                return []

            rows = table.find_all("tr")
            # Extract headers from first row
            headers = []
            header_row = rows[0] if rows else None
            if header_row:
                headers = [
                    cell.get_text(strip=True).lower().replace(" ", "_")
                    for cell in header_row.find_all(["th", "td"])
                ]

            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                values = [cell.get_text(strip=True) for cell in cells]
                row_dict = dict(zip(headers, values)) if headers else {}

                # Map to our schema based on known column positions
                # Columns: Org Name, POA, Org Phone, Org City, Org State,
                #          Representative, Rep City, Rep State, Rep Zip, Reg Num
                org_name = row_dict.get("organization_name", "") or (values[0] if len(values) > 0 else "")
                phone = row_dict.get("org_phone", "") or (values[2] if len(values) > 2 else "")
                city = row_dict.get("org_city", "") or (values[3] if len(values) > 3 else "")
                state = row_dict.get("org_state", "") or (values[4] if len(values) > 4 else "")
                rep_name = row_dict.get("representative", "") or (values[5] if len(values) > 5 else "")

                if org_name:
                    records.append({
                        "org_name": org_name,
                        "city": city,
                        "state": state,
                        "phone": phone,
                        "representative_name": rep_name,
                        "va_accredited": "Yes",
                        "accreditation_details": f"VA-Accredited VSO; Rep: {rep_name}" if rep_name else "VA-Accredited VSO",
                    })

        except Exception as e:
            self.logger.warning(f"Error fetching VSO orgs Excel dump: {e}")

        return records

    def _fetch_via_search(self) -> list[dict]:
        """Fallback: POST to search endpoint with blank fields for all orgs."""
        records = []
        try:
            # Empty fields returns all organizations
            form_data = {
                "Name": "",
                "City": "",
                "State": "",
                "Zip": "",
            }
            resp = self.http.post(VSO_SEARCH_URL, data=form_data)
            if resp.status_code != 200:
                return []

            soup = BeautifulSoup(resp.text, "lxml")
            table = soup.find("table")
            if not table:
                return []

            rows = table.find_all("tr")
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) < 3:
                    continue

                values = [cell.get_text(strip=True) for cell in cells]
                org_name = values[0] if len(values) > 0 else ""
                city = values[1] if len(values) > 1 else ""
                state = values[2] if len(values) > 2 else ""
                zipcode = values[3] if len(values) > 3 else ""
                phone = values[4] if len(values) > 4 else ""

                if org_name:
                    records.append({
                        "org_name": org_name,
                        "city": city,
                        "state": state,
                        "zip_code": zipcode,
                        "phone": phone,
                        "va_accredited": "Yes",
                        "accreditation_details": "VA-Accredited VSO",
                    })

        except Exception as e:
            self.logger.warning(f"Error in VSO search fallback: {e}")

        return records

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = pd.DataFrame()
        out["org_name"] = df["org_name"].str.strip().str.title()
        out["city"] = df.get("city", pd.Series(dtype="string")).str.strip().str.title()
        out["state"] = df.get("state", pd.Series(dtype="string")).str.strip().str.upper()
        out["zip_code"] = df.get("zip_code", pd.Series(dtype="string"))
        out["phone"] = df.get("phone", pd.Series(dtype="string"))
        out["va_accredited"] = "Yes"
        out["accreditation_details"] = df.get("accreditation_details")

        # Aggregate representatives per org into key_personnel JSON
        if "representative_name" in df.columns:
            rep_groups = df.groupby("org_name")["representative_name"].apply(
                lambda x: json.dumps([{"name": n, "title": "VSO Representative"} for n in x if n])
            )
            out["key_personnel"] = df["org_name"].map(rep_groups)

        return out

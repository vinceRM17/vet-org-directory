"""VA Lighthouse Facilities API extractor.

Paginates through all VA facilities (health, benefits, cemetery, vet centers)
to build a directory of ~1,700 VA facilities with services and contact info.
"""

from __future__ import annotations

import logging

import pandas as pd

from config.settings import (
    VA_FACILITIES_API_KEY,
    VA_FACILITIES_BASE_URL,
    VA_FACILITIES_RATE_LIMIT,
)
from extractors.base_extractor import BaseExtractor
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

FACILITY_TYPES = ["health", "benefits", "cemetery", "vet_center"]


class VaFacilitiesExtractor(BaseExtractor):
    name = "va_facilities"

    def __init__(self):
        super().__init__()
        self.http = RateLimitedSession(
            rate_limit=VA_FACILITIES_RATE_LIMIT,
            cache_name="va_facilities",
        )

    def extract(self) -> pd.DataFrame:
        if not VA_FACILITIES_API_KEY:
            self.logger.warning(
                "VA_FACILITIES_API_KEY not set — skipping VA Facilities"
            )
            return pd.DataFrame()

        all_records = []
        for ftype in FACILITY_TYPES:
            try:
                records = self._fetch_facilities(ftype)
                all_records.extend(records)
                self.logger.info(f"VA Facilities ({ftype}): {len(records)} records")
            except Exception as e:
                self.logger.warning(f"Error fetching VA {ftype} facilities: {e}")

        return pd.DataFrame(all_records) if all_records else pd.DataFrame()

    def _fetch_facilities(self, facility_type: str) -> list[dict]:
        records = []
        page = 1
        per_page = 200

        while True:
            params = {
                "type": facility_type,
                "page": page,
                "per_page": per_page,
            }
            headers = {"apikey": VA_FACILITIES_API_KEY}
            resp = self.http.get(
                VA_FACILITIES_BASE_URL, params=params, headers=headers
            )

            if resp.status_code != 200:
                self.logger.warning(
                    f"VA Facilities API returned {resp.status_code} for {facility_type} page {page}"
                )
                break

            data = resp.json()
            facilities = data.get("data", [])
            if not facilities:
                break

            for f in facilities:
                attrs = f.get("attributes", {})
                address = attrs.get("address", {}).get("physical", {})
                phone = attrs.get("phone", {}).get("main", "")
                hours = attrs.get("hours", {})

                services = []
                for svc in attrs.get("services", {}).get("health", []):
                    if isinstance(svc, dict):
                        services.append(svc.get("name", ""))
                    elif isinstance(svc, str):
                        services.append(svc)

                records.append({
                    "facility_id": f.get("id", ""),
                    "org_name": attrs.get("name", ""),
                    "facility_type": facility_type,
                    "street_address": address.get("address_1", ""),
                    "street_address_2": address.get("address_2", ""),
                    "city": address.get("city", ""),
                    "state": address.get("state", ""),
                    "zip_code": address.get("zip", ""),
                    "phone": phone,
                    "website": attrs.get("website", ""),
                    "services_offered": "; ".join(services) if services else "",
                    "hours": str(hours) if hours else "",
                    "lat": attrs.get("lat"),
                    "long": attrs.get("long"),
                })

            # Check for more pages
            meta = data.get("meta", {}).get("pagination", {})
            total_pages = meta.get("totalPages", 1)
            if page >= total_pages:
                break
            page += 1

        return records

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = pd.DataFrame()
        out["org_name"] = df["org_name"].str.strip()
        out["street_address"] = df["street_address"].str.strip()
        out["street_address_2"] = df.get("street_address_2", pd.Series(dtype="string"))
        out["city"] = df["city"].str.strip().str.title()
        out["state"] = df["state"].str.strip().str.upper()
        out["zip_code"] = df["zip_code"].str.strip()
        out["country"] = "US"
        out["phone"] = df["phone"]
        out["website"] = df["website"]
        out["services_offered"] = df["services_offered"]
        out["org_type"] = "VA Facility"
        out["va_accredited"] = "Yes"
        out["accreditation_details"] = "VA " + df["facility_type"].str.replace("_", " ").str.title()
        return out

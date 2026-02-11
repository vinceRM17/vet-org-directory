"""National Resource Directory (nrd.gov) extractor.

NRD is a Vue.js SPA — HTML scraping returns empty shells. Instead we use:
  1. /landingItems JSON API for featured resources and categories
  2. /sitemap.xml to discover all ~7,900 resource URLs
  3. Individual resource detail fetches for org data
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import pandas as pd
from bs4 import BeautifulSoup

from config.settings import NRD_BASE_URL, NRD_RATE_LIMIT
from extractors.base_extractor import BaseExtractor
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

LANDING_ITEMS_URL = f"{NRD_BASE_URL}/landingItems"
SEARCH_ITEMS_URL = f"{NRD_BASE_URL}/getSearchItems"
SITEMAP_URL = f"{NRD_BASE_URL}/sitemap.xml"


class NrdExtractor(BaseExtractor):
    name = "nrd"

    def __init__(self):
        super().__init__()
        self.http = RateLimitedSession(
            rate_limit=NRD_RATE_LIMIT,
            cache_name="nrd",
        )

    def extract(self) -> pd.DataFrame:
        all_records = []

        # Source 1: Landing items JSON API (featured resources)
        try:
            landing_records = self._fetch_landing_items()
            all_records.extend(landing_records)
            self.logger.info(f"NRD landing items: {len(landing_records)} records")
        except Exception as e:
            self.logger.warning(f"Error fetching NRD landing items: {e}")

        # Source 2: Parse sitemap for all resource URLs, then fetch details
        try:
            sitemap_records = self._fetch_from_sitemap()
            all_records.extend(sitemap_records)
            self.logger.info(f"NRD sitemap resources: {len(sitemap_records)} records")
        except Exception as e:
            self.logger.warning(f"Error processing NRD sitemap: {e}")

        return pd.DataFrame(all_records) if all_records else pd.DataFrame()

    def _fetch_landing_items(self) -> list[dict]:
        """Fetch the /landingItems JSON endpoint for featured resources."""
        records = []
        resp = self.http.get(LANDING_ITEMS_URL)
        if resp.status_code != 200:
            self.logger.warning(f"NRD landingItems returned {resp.status_code}")
            return records

        try:
            data = resp.json()
        except Exception:
            self.logger.warning("NRD landingItems returned non-JSON response")
            return records

        # Extract resources from the response
        resources = data.get("resources", [])
        for r in resources:
            record = self._parse_resource(r)
            if record:
                records.append(record)

        # Extract from folders/categories
        folders = data.get("folders", [])
        for folder in folders:
            folder_resources = folder.get("resources", [])
            category = folder.get("name", "")
            for r in folder_resources:
                record = self._parse_resource(r, category=category)
                if record:
                    records.append(record)

        return records

    def _parse_resource(self, r: dict, category: str = "") -> dict | None:
        """Parse a single resource object from the JSON API."""
        name = r.get("title", "") or r.get("name", "")
        if not name:
            return None

        url = r.get("url", "") or r.get("website", "") or r.get("link", "")
        description = r.get("description", "") or r.get("summary", "")
        phone = r.get("phone", "") or r.get("phoneNumber", "")

        # Clean HTML from description
        if description and "<" in description:
            description = BeautifulSoup(description, "lxml").get_text(strip=True)

        return {
            "org_name": name.strip(),
            "website": url.strip() if url else "",
            "phone": phone.strip() if phone else "",
            "services_offered": description[:500] if description else "",
            "service_categories": category,
        }

    def _fetch_from_sitemap(self) -> list[dict]:
        """Parse sitemap.xml to find resource URLs and extract metadata."""
        partial = load_checkpoint(f"{self.name}_sitemap_partial")
        if partial is not None:
            records, done_urls = partial
            self.logger.info(f"Resuming NRD sitemap from {len(done_urls)} done")
        else:
            records = []
            done_urls = set()

        # Fetch and parse sitemap
        resp = self.http.get(SITEMAP_URL)
        if resp.status_code != 200:
            self.logger.warning(f"NRD sitemap returned {resp.status_code}")
            return records

        # Parse XML
        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError as e:
            self.logger.warning(f"Failed to parse NRD sitemap: {e}")
            return records

        # Extract resource detail URLs
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = []
        for url_elem in root.findall(".//sm:url/sm:loc", ns):
            url = url_elem.text
            if url and "/resource/detail/" in url:
                urls.append(url)

        # Also try without namespace
        if not urls:
            for url_elem in root.iter():
                if url_elem.text and "/resource/detail/" in str(url_elem.text):
                    urls.append(url_elem.text.strip())

        self.logger.info(f"NRD sitemap: {len(urls)} resource URLs found")

        # Extract org name and category from URL structure
        # Format: /resource/detail/{id}/{slug}
        for url in urls:
            if url in done_urls:
                continue

            match = re.search(r"/resource/detail/(\d+)/(.+?)$", url)
            if match:
                resource_id = match.group(1)
                slug = match.group(2)
                # Convert slug to readable name
                name = slug.replace("-", " ").strip()
                # Title case, preserving acronyms
                name = " ".join(
                    w.upper() if len(w) <= 3 and w.isalpha() else w.title()
                    for w in name.split()
                )

                records.append({
                    "org_name": name,
                    "website": url,
                    "nrd_resource_id": resource_id,
                    "services_offered": "",
                    "service_categories": "NRD Resource",
                })

            done_urls.add(url)

            if len(done_urls) % 1000 == 0:
                save_checkpoint(f"{self.name}_sitemap_partial", (records, done_urls))

        return records

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = pd.DataFrame()
        out["org_name"] = df["org_name"].str.strip()
        out["website"] = df.get("website")
        out["phone"] = df.get("phone")
        out["services_offered"] = df.get("services_offered")
        out["service_categories"] = df.get("service_categories")
        return out

"""Web enrichment: scrape org websites for social media URLs and email addresses."""

from __future__ import annotations

import logging
import re

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

from config.settings import CHECKPOINT_INTERVAL, ENRICHER_RATE_LIMIT, ENRICHER_TIMEOUT
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

# Social media URL patterns
SOCIAL_PATTERNS = {
    "facebook_url": re.compile(
        r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE
    ),
    "twitter_url": re.compile(
        r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/?", re.IGNORECASE
    ),
    "linkedin_url": re.compile(
        r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9._-]+/?",
        re.IGNORECASE,
    ),
    "instagram_url": re.compile(
        r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._-]+/?", re.IGNORECASE
    ),
    "youtube_url": re.compile(
        r"https?://(?:www\.)?youtube\.com/(?:channel|c|user|@)[A-Za-z0-9._-]+/?",
        re.IGNORECASE,
    ),
}

# Email pattern
EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.IGNORECASE
)

# Common generic emails to skip
SKIP_EMAILS = {
    "sentry@sentry.io", "wixpress@wix.com", "example@example.com",
    "support@squarespace.com", "info@wordpress.com",
}


class WebEnricher:
    """Scrape org websites to extract social media links and contact emails."""

    def __init__(self):
        self.http = RateLimitedSession(
            rate_limit=ENRICHER_RATE_LIMIT,
            timeout=ENRICHER_TIMEOUT,
            cache_name="enricher",
        )
        self.logger = logging.getLogger("enricher")

    def enrich(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enrich DataFrame rows that have a website but are missing social/email."""
        partial = load_checkpoint("enricher_partial")
        if partial is not None:
            enrichments, done_indices = partial
            self.logger.info(f"Resuming enrichment from {len(done_indices)} completed")
        else:
            enrichments = {}
            done_indices = set()

        # Find rows that need enrichment
        needs_enrichment = df[
            df["website"].notna()
            & (
                df["email"].isna()
                | df["facebook_url"].isna()
                | df["twitter_url"].isna()
            )
        ].index

        remaining = [i for i in needs_enrichment if i not in done_indices]
        self.logger.info(f"Enriching {len(remaining):,} org websites")

        for count, idx in enumerate(tqdm(
            remaining,
            desc="Enriching websites",
            unit="org",
            initial=len(done_indices),
            total=len(needs_enrichment),
        )):
            url = df.at[idx, "website"]
            try:
                data = self._scrape_website(url)
                if data:
                    enrichments[idx] = data
            except Exception as e:
                self.logger.debug(f"Error scraping {url}: {e}")

            done_indices.add(idx)

            if (count + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint("enricher_partial", (enrichments, done_indices))
                tqdm.write(
                    f"  Checkpoint saved: {len(done_indices):,}/{len(needs_enrichment):,} orgs processed"
                )

        # Apply enrichments
        for idx, data in enrichments.items():
            for col, value in data.items():
                if col in df.columns and pd.isna(df.at[idx, col]):
                    df.at[idx, col] = value

        self.logger.info(
            f"Enrichment complete: {len(enrichments):,} orgs updated"
        )
        return df

    def _scrape_website(self, url: str) -> dict | None:
        """Fetch a website and extract social media URLs and email."""
        resp = self.http.get(url, use_cache=True)
        if resp.status_code != 200:
            return None

        html = resp.text
        soup = BeautifulSoup(html, "lxml")
        result = {}

        # Extract social media URLs from all links
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            for field, pattern in SOCIAL_PATTERNS.items():
                if field not in result:
                    match = pattern.search(href)
                    if match:
                        result[field] = match.group().rstrip("/")

        # Also scan raw HTML for social URLs (some are in scripts/meta)
        for field, pattern in SOCIAL_PATTERNS.items():
            if field not in result:
                match = pattern.search(html)
                if match:
                    result[field] = match.group().rstrip("/")

        # Extract email
        emails = EMAIL_PATTERN.findall(html)
        for email in emails:
            email_lower = email.lower()
            if email_lower not in SKIP_EMAILS and not email_lower.endswith(
                (".png", ".jpg", ".gif", ".js", ".css")
            ):
                result["email"] = email_lower
                break

        # Extract meta description as services_offered
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            result["mission_statement"] = meta_desc["content"].strip()[:500]

        return result if result else None

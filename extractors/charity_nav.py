"""Charity Navigator GraphQL API extractor for ratings and mission data."""

from __future__ import annotations

import json
import logging

import pandas as pd

from config.settings import (
    CHARITY_NAV_API_KEY,
    CHARITY_NAV_GRAPHQL_URL,
    CHARITY_NAV_RATE_LIMIT,
    CHECKPOINT_INTERVAL,
)
from extractors.base_extractor import BaseExtractor
from utils.checkpoint import load_checkpoint, save_checkpoint
from utils.http_client import RateLimitedSession

logger = logging.getLogger(__name__)

# GraphQL query for org details by EIN
QUERY = """
query GetOrgByEIN($ein: String!) {
  organizationByEIN(ein: $ein) {
    name
    ein
    mission
    websiteURL
    currentRating {
      score
      rating
      ratingImage {
        small
      }
    }
    advisories {
      severity
      description {
        text
      }
    }
    socialMedia {
      facebookProfileUrl
      twitterHandle
      linkedinUrl
      instagramHandle
      youtubeUrl
    }
  }
}
"""


class CharityNavExtractor(BaseExtractor):
    name = "charity_nav"

    def __init__(self, ein_list: list[str] | None = None):
        super().__init__()
        self.ein_list = ein_list or []
        self.http = RateLimitedSession(
            rate_limit=CHARITY_NAV_RATE_LIMIT,
            cache_name="charity_nav",
        )

    def extract(self) -> pd.DataFrame:
        if not CHARITY_NAV_API_KEY:
            self.logger.warning(
                "CHARITY_NAVIGATOR_API_KEY not set — skipping Charity Navigator"
            )
            return pd.DataFrame()

        partial = load_checkpoint(f"{self.name}_partial")
        if partial is not None:
            records, done_eins = partial
            self.logger.info(f"Resuming from {len(done_eins):,} completed EINs")
        else:
            records = []
            done_eins = set()

        remaining = [e for e in self.ein_list if e not in done_eins]
        self.logger.info(f"Fetching {len(remaining):,} EINs from Charity Navigator")

        for i, ein in enumerate(remaining):
            try:
                data = self._fetch_ein(ein)
                if data:
                    records.append(data)
            except Exception as e:
                self.logger.warning(f"Error fetching CN EIN {ein}: {e}")

            done_eins.add(ein)

            if (i + 1) % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(f"{self.name}_partial", (records, done_eins))
                self.logger.info(
                    f"CharityNav progress: {len(done_eins):,}/{len(self.ein_list):,}"
                )

        return pd.DataFrame(records) if records else pd.DataFrame()

    def _fetch_ein(self, ein: str) -> dict | None:
        payload = {
            "query": QUERY,
            "variables": {"ein": ein},
        }
        headers = {
            "Content-Type": "application/json",
            "Charity-Navigator-Api-Key": CHARITY_NAV_API_KEY,
        }
        resp = self.http.post(
            CHARITY_NAV_GRAPHQL_URL, json=payload, headers=headers
        )
        if resp.status_code != 200:
            return None

        body = resp.json()
        org = (body.get("data") or {}).get("organizationByEIN")
        if not org:
            return None

        rating = org.get("currentRating") or {}
        advisories = org.get("advisories") or []
        social = org.get("socialMedia") or {}

        alert_level = None
        if advisories:
            alert_level = advisories[0].get("severity", "")

        twitter_handle = social.get("twitterHandle", "")
        twitter_url = f"https://twitter.com/{twitter_handle}" if twitter_handle else None

        instagram_handle = social.get("instagramHandle", "")
        instagram_url = (
            f"https://instagram.com/{instagram_handle}" if instagram_handle else None
        )

        return {
            "ein": ein,
            "mission_statement": org.get("mission"),
            "website": org.get("websiteURL"),
            "charity_navigator_rating": rating.get("rating"),
            "charity_navigator_score": rating.get("score"),
            "cn_alert_level": alert_level,
            "facebook_url": social.get("facebookProfileUrl"),
            "twitter_url": twitter_url,
            "linkedin_url": social.get("linkedinUrl"),
            "instagram_url": instagram_url,
            "youtube_url": social.get("youtubeUrl"),
        }

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
        out = pd.DataFrame()
        out["ein"] = df["ein"]
        out["mission_statement"] = df.get("mission_statement")
        out["website"] = df.get("website")
        out["charity_navigator_rating"] = pd.to_numeric(
            df.get("charity_navigator_rating"), errors="coerce"
        )
        out["charity_navigator_score"] = pd.to_numeric(
            df.get("charity_navigator_score"), errors="coerce"
        )
        out["cn_alert_level"] = df.get("cn_alert_level")
        out["facebook_url"] = df.get("facebook_url")
        out["twitter_url"] = df.get("twitter_url")
        out["linkedin_url"] = df.get("linkedin_url")
        out["instagram_url"] = df.get("instagram_url")
        out["youtube_url"] = df.get("youtube_url")
        return out

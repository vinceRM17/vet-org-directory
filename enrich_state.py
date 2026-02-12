#!/usr/bin/env python3
"""
State-focused enrichment: discover websites via web search, then scrape
for email, phone, social media, and mission statements.

Usage:
    python enrich_state.py KY              # Enrich all KY orgs
    python enrich_state.py KY --resume     # Resume from checkpoint
    python enrich_state.py KY --limit 50   # Only do first 50
"""

import argparse
import csv
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

try:
    from duckduckgo_search import DDGS
except ImportError:
    from ddgs import DDGS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("enrich_state")

# ── Paths ──
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_CSV = DATA_DIR / "output" / "veteran_org_directory.csv"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

# ── Patterns ──
PHONE_RE = re.compile(r"\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}")
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

SOCIAL_PATTERNS = {
    "facebook_url": re.compile(r"https?://(?:www\.)?facebook\.com/[A-Za-z0-9._\-]+/?", re.I),
    "twitter_url": re.compile(r"https?://(?:www\.)?(?:twitter|x)\.com/[A-Za-z0-9_]+/?", re.I),
    "linkedin_url": re.compile(r"https?://(?:www\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9._\-]+/?", re.I),
    "instagram_url": re.compile(r"https?://(?:www\.)?instagram\.com/[A-Za-z0-9._\-]+/?", re.I),
    "youtube_url": re.compile(r"https?://(?:www\.)?youtube\.com/(?:channel|c|user|@)[A-Za-z0-9._\-]+/?", re.I),
}

# Generic social URLs that are share buttons / not real org pages
SKIP_SOCIAL_URLS = {
    "facebook.com/sharer", "facebook.com/share", "facebook.com/dialog",
    "facebook.com/login", "facebook.com/help", "facebook.com/policies",
    "twitter.com/intent", "twitter.com/share", "twitter.com/home",
    "x.com/intent", "x.com/share",
    "linkedin.com/company/stack-overflow", "linkedin.com/shareArticle",
    "linkedin.com/company/linkedin",
    "instagram.com/accounts", "instagram.com/explore",
    "instagram.com/thestackoverflow",
    "youtube.com/@youtube",
}

# Domains to skip when identifying org websites
SKIP_DOMAINS = {
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
    "yelp.com", "yellowpages.com", "bbb.org", "mapquest.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "youtube.com", "tiktok.com", "pinterest.com",
    "wikipedia.org", "indeed.com", "glassdoor.com", "manta.com",
    "guidestar.org", "candid.org", "charitynavigator.org",
    "propublica.org", "nonprofitfacts.com", "cause-iq.com",
    "greatnonprofits.org", "give.org", "idealist.org",
    "boardsource.org", "council-of-nonprofits.org",
    "amazon.com", "ebay.com", "walmart.com", "target.com",
    "reddit.com", "quora.com", "medium.com",
}

# Emails to skip (generic / template)
SKIP_EMAIL_PATTERNS = [
    "example.com", "wixpress", "sentry", "webpack",
    "googleapis", "schema.org", "w3.org", "jquery",
    "godaddy", "squarespace", "wordpress", "shopify",
    "wix.com", "weebly", "cloudflare", "cpanel",
    "placeholder", "yourname", "youremail", "noreply",
    "sentry.io", ".png", ".jpg", ".gif", ".js", ".css",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


def load_checkpoint(state_code):
    """Load enrichment checkpoint for a state."""
    path = CHECKPOINT_DIR / f"enrich_{state_code.lower()}.json"
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {"done_eins": [], "enrichments": {}}


def save_checkpoint(state_code, data):
    """Save enrichment checkpoint."""
    path = CHECKPOINT_DIR / f"enrich_{state_code.lower()}.json"
    with open(path, "w") as f:
        json.dump(data, f)


def search_web(query, max_results=8):
    """Search DuckDuckGo for an organization."""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return [
                {"url": r.get("href", ""), "title": r.get("title", ""), "snippet": r.get("body", "")}
                for r in results
            ]
    except Exception as e:
        logger.debug(f"Search error: {e}")
        return []


def extract_website(results):
    """Find the most likely org website from search results."""
    for r in results:
        try:
            domain = urlparse(r["url"]).netloc.lower().replace("www.", "")
        except Exception:
            continue
        if any(skip in domain for skip in SKIP_DOMAINS):
            continue
        return r["url"]
    return ""


def extract_phone_from_snippets(results):
    """Pull phone numbers from search result snippets."""
    for r in results:
        text = r.get("snippet", "") + " " + r.get("title", "")
        match = PHONE_RE.search(text)
        if match:
            return match.group(0)
    return ""


def extract_email_from_snippets(results):
    """Pull email from search result snippets."""
    for r in results:
        text = r.get("snippet", "") + " " + r.get("title", "")
        match = EMAIL_RE.search(text)
        if match:
            email = match.group(0)
            if not any(skip in email.lower() for skip in SKIP_EMAIL_PATTERNS):
                return email
    return ""


def _is_valid_social(url):
    """Filter out generic share/login social URLs."""
    url_lower = url.lower()
    return not any(skip in url_lower for skip in SKIP_SOCIAL_URLS)


def extract_socials_from_results(results):
    """Pull social media URLs from search results."""
    socials = {}
    for r in results:
        url = r.get("url", "")
        for platform, pattern in SOCIAL_PATTERNS.items():
            if platform not in socials:
                match = pattern.search(url)
                if match and _is_valid_social(match.group(0)):
                    socials[platform] = match.group(0).rstrip("/")
    return socials


def scrape_website(url):
    """Visit an org website and extract contact info."""
    info = {"phone": "", "email": "", "socials": {}, "mission": ""}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if resp.status_code != 200:
            return info

        html = resp.text
        soup = BeautifulSoup(html, "lxml")

        # Phone
        match = PHONE_RE.search(html)
        if match:
            info["phone"] = match.group(0)

        # Email — check mailto links first
        for a in soup.find_all("a", href=True):
            if a["href"].startswith("mailto:"):
                email = a["href"].replace("mailto:", "").split("?")[0].strip()
                if EMAIL_RE.match(email) and not any(s in email.lower() for s in SKIP_EMAIL_PATTERNS):
                    info["email"] = email.lower()
                    break

        if not info["email"]:
            emails = EMAIL_RE.findall(html)
            for email in emails:
                if not any(s in email.lower() for s in SKIP_EMAIL_PATTERNS):
                    info["email"] = email.lower()
                    break

        # Social links
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            for platform, pattern in SOCIAL_PATTERNS.items():
                if platform not in info["socials"]:
                    match = pattern.search(href)
                    if match and _is_valid_social(match.group(0)):
                        info["socials"][platform] = match.group(0).rstrip("/")

        # Also scan raw HTML for social URLs
        for platform, pattern in SOCIAL_PATTERNS.items():
            if platform not in info["socials"]:
                match = pattern.search(html)
                if match and _is_valid_social(match.group(0)):
                    info["socials"][platform] = match.group(0).rstrip("/")

        # Mission statement from meta description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            info["mission"] = str(meta_desc["content"]).strip()[:500]

    except Exception as e:
        logger.debug(f"Scrape error for {url}: {e}")

    return info


def enrich_org(org_name, city, state):
    """Search for an org and extract all available contact info."""
    query = f'"{org_name}" {city} {state} nonprofit'
    results = search_web(query)

    if not results:
        return None

    website = extract_website(results)
    phone = extract_phone_from_snippets(results)
    email = extract_email_from_snippets(results)
    socials = extract_socials_from_results(results)

    # If we found a website, scrape it for more info
    site_info = {"phone": "", "email": "", "socials": {}, "mission": ""}
    if website:
        site_info = scrape_website(website)
        if not phone and site_info["phone"]:
            phone = site_info["phone"]
        if not email and site_info["email"]:
            email = site_info["email"]
        for k, v in site_info["socials"].items():
            if k not in socials:
                socials[k] = v

    return {
        "website": website,
        "phone": phone,
        "email": email,
        "mission_statement": site_info["mission"],
        **socials,
    }


def main():
    parser = argparse.ArgumentParser(description="Enrich veteran orgs by state")
    parser.add_argument("state", help="2-letter state code (e.g., KY)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of orgs to process")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds between searches")
    args = parser.parse_args()

    state = args.state.upper()

    # Load CSV
    logger.info(f"Loading {OUTPUT_CSV}")
    import pandas as pd
    df = pd.read_csv(OUTPUT_CSV, low_memory=False)

    # Filter to state
    state_mask = df["state"].str.upper() == state
    state_df = df[state_mask].copy()
    logger.info(f"Found {len(state_df):,} orgs in {state}")

    # Load checkpoint
    ckpt = {"done_eins": [], "enrichments": {}}
    if args.resume:
        ckpt = load_checkpoint(state)
        logger.info(f"Resuming: {len(ckpt['done_eins'])} already done")

    done_set = set(ckpt["done_eins"])
    enrichments = ckpt["enrichments"]

    # Build work queue
    work = []
    for idx, row in state_df.iterrows():
        ein = str(row.get("ein", ""))
        if ein and ein in done_set:
            continue
        work.append((idx, ein, row["org_name"], row.get("city", ""), state))

    if args.limit > 0:
        work = work[:args.limit]

    logger.info(f"Enriching {len(work):,} orgs...")
    found_count = 0

    for i, (idx, ein, name, city, st) in enumerate(tqdm(work, desc=f"Enriching {state}", unit="org")):
        try:
            info = enrich_org(name, city, st)
        except Exception as e:
            logger.warning(f"Error on {name}: {e}")
            time.sleep(3)
            if ein:
                done_set.add(ein)
                ckpt["done_eins"] = list(done_set)
            continue

        if ein:
            done_set.add(ein)
            ckpt["done_eins"] = list(done_set)

        if info:
            found_fields = [k for k, v in info.items() if v]
            if found_fields:
                enrichments[str(idx)] = info
                found_count += 1
                tqdm.write(f"  {name}: {', '.join(found_fields)}")

        # Checkpoint every 50
        if (i + 1) % 50 == 0:
            ckpt["enrichments"] = enrichments
            save_checkpoint(state, ckpt)
            tqdm.write(f"  Checkpoint saved: {len(done_set)}/{len(work) + len(done_set) - len(work)} done, {found_count} enriched")

        time.sleep(args.delay)

    # Final checkpoint
    ckpt["enrichments"] = enrichments
    save_checkpoint(state, ckpt)

    # Apply enrichments to DataFrame
    logger.info(f"Applying {len(enrichments):,} enrichments to CSV...")
    fields_to_update = [
        "website", "phone", "email", "mission_statement",
        "facebook_url", "twitter_url", "linkedin_url", "instagram_url", "youtube_url",
    ]

    updated = 0
    for idx_str, info in enrichments.items():
        idx = int(idx_str)
        for field in fields_to_update:
            value = info.get(field, "")
            if value and (pd.isna(df.at[idx, field]) or df.at[idx, field] == ""):
                df.at[idx, field] = value
                updated += 1

    # Save updated CSV
    df.to_csv(OUTPUT_CSV, index=False)
    logger.info(f"Saved {OUTPUT_CSV}")

    # Print summary
    state_df_updated = df[state_mask]
    print(f"\n{'='*50}")
    print(f"ENRICHMENT SUMMARY — {state}")
    print(f"{'='*50}")
    print(f"Total {state} orgs:    {len(state_df_updated):,}")
    print(f"Orgs processed:       {len(done_set):,}")
    print(f"Orgs with new data:   {found_count:,}")
    print(f"Fields updated:       {updated:,}")
    print()
    for col in fields_to_update:
        count = state_df_updated[col].notna().sum()
        pct = count / len(state_df_updated) * 100
        print(f"  {col:25s}: {count:>5,} / {len(state_df_updated):,}  ({pct:.1f}%)")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()

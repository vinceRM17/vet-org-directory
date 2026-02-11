"""Three-tier deduplication: EIN exact → fuzzy name+city → URL domain."""

import logging
from urllib.parse import urlparse

import pandas as pd
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


def deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    """Run all three dedup tiers in sequence."""
    logger.info(f"Deduplication starting with {len(df):,} records")

    df = _tier1_exact_ein(df)
    logger.info(f"After EIN dedup: {len(df):,} records")

    df = _tier2_fuzzy_name_city(df)
    logger.info(f"After fuzzy name+city dedup: {len(df):,} records")

    df = _tier3_url_domain(df)
    logger.info(f"After URL domain dedup: {len(df):,} records")

    return df.reset_index(drop=True)


def _merge_rows(group: pd.DataFrame) -> pd.Series:
    """Merge a group of duplicate rows, keeping the most complete fields."""
    if len(group) == 1:
        return group.iloc[0]

    result = group.iloc[0].copy()
    for col in group.columns:
        if pd.isna(result[col]):
            # Find first non-null value
            non_null = group[col].dropna()
            if len(non_null) > 0:
                result[col] = non_null.iloc[0]

    # Merge data_sources
    sources = set()
    for val in group["data_sources"].dropna():
        sources.update(val.split(";"))
    sources.discard("")
    result["data_sources"] = ";".join(sorted(sources))

    return result


def _tier1_exact_ein(df: pd.DataFrame) -> pd.DataFrame:
    """Tier 1: Merge records with identical EINs."""
    has_ein = df["ein"].notna() & (df["ein"] != "")
    with_ein = df[has_ein]
    without_ein = df[~has_ein]

    if with_ein.empty:
        return df

    dupes = with_ein.duplicated(subset=["ein"], keep=False)
    unique = with_ein[~dupes]
    duplicated = with_ein[dupes]

    if duplicated.empty:
        return df

    logger.info(f"Tier 1: Merging {len(duplicated):,} records with duplicate EINs")
    merged = duplicated.groupby("ein", group_keys=False).apply(_merge_rows)
    merged = merged.reset_index(drop=True) if isinstance(merged, pd.DataFrame) else merged.to_frame().T

    return pd.concat([unique, merged, without_ein], ignore_index=True)


def _tier2_fuzzy_name_city(df: pd.DataFrame, threshold: float = 85.0) -> pd.DataFrame:
    """Tier 2: Fuzzy match on org_name within same city+state."""
    has_location = df["city"].notna() & df["state"].notna() & df["org_name"].notna()
    candidates = df[has_location].copy()
    no_location = df[~has_location]

    if candidates.empty or len(candidates) < 2:
        return df

    # Group by state+city, then fuzzy match within groups
    candidates["_group_key"] = (
        candidates["state"].str.upper() + "|" + candidates["city"].str.upper()
    )

    merge_map = {}  # index → group_id
    group_counter = 0

    for group_key, group in candidates.groupby("_group_key"):
        if len(group) < 2:
            continue

        indices = group.index.tolist()
        names = group["org_name"].tolist()

        matched = set()
        for i in range(len(indices)):
            if indices[i] in matched:
                continue
            cluster = [indices[i]]
            for j in range(i + 1, len(indices)):
                if indices[j] in matched:
                    continue
                score = fuzz.token_sort_ratio(names[i], names[j])
                if score >= threshold:
                    cluster.append(indices[j])
                    matched.add(indices[j])

            if len(cluster) > 1:
                for idx in cluster:
                    merge_map[idx] = group_counter
                group_counter += 1

    if not merge_map:
        candidates.drop(columns=["_group_key"], inplace=True)
        return pd.concat([candidates, no_location], ignore_index=True)

    logger.info(f"Tier 2: Found {len(merge_map):,} records in {group_counter} fuzzy groups")

    # Separate merged and unmerged
    to_merge_idx = set(merge_map.keys())
    unmerged = candidates[~candidates.index.isin(to_merge_idx)]
    to_merge = candidates[candidates.index.isin(to_merge_idx)].copy()
    to_merge["_merge_group"] = to_merge.index.map(merge_map)

    merged = (
        to_merge.drop(columns=["_group_key"])
        .groupby("_merge_group", group_keys=False)
        .apply(_merge_rows)
    )
    if isinstance(merged, pd.Series):
        merged = merged.to_frame().T
    merged = merged.reset_index(drop=True)
    if "_merge_group" in merged.columns:
        merged.drop(columns=["_merge_group"], inplace=True)

    unmerged.drop(columns=["_group_key"], inplace=True)

    return pd.concat([unmerged, merged, no_location], ignore_index=True)


def _tier3_url_domain(df: pd.DataFrame) -> pd.DataFrame:
    """Tier 3: Merge records with the same root URL domain."""
    has_url = df["website"].notna() & (df["website"] != "")
    with_url = df[has_url].copy()
    without_url = df[~has_url]

    if with_url.empty or len(with_url) < 2:
        return df

    # Extract root domain
    def get_domain(url):
        try:
            parsed = urlparse(str(url))
            domain = parsed.netloc.lower()
            # Remove www.
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    with_url["_domain"] = with_url["website"].apply(get_domain)
    with_url = with_url[with_url["_domain"] != ""]

    dupes = with_url.duplicated(subset=["_domain"], keep=False)
    unique = with_url[~dupes]
    duplicated = with_url[dupes]

    if duplicated.empty:
        with_url.drop(columns=["_domain"], inplace=True)
        return pd.concat([with_url, without_url], ignore_index=True)

    logger.info(f"Tier 3: Merging {len(duplicated):,} records with duplicate domains")
    merged = duplicated.groupby("_domain", group_keys=False).apply(_merge_rows)
    if isinstance(merged, pd.Series):
        merged = merged.to_frame().T
    merged = merged.reset_index(drop=True)

    for part in (unique, merged):
        if "_domain" in part.columns:
            part.drop(columns=["_domain"], inplace=True, errors="ignore")

    return pd.concat([unique, merged, without_url], ignore_index=True)

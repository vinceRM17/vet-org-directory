"""Multi-source merge with priority rules.

IRS BMF is the base; other sources fill in blanks without overwriting
higher-priority data.
"""

from __future__ import annotations

import logging

import pandas as pd

from config.schema import COLUMN_NAMES, coerce_schema

logger = logging.getLogger(__name__)

# Priority order: lower index = higher priority for field values
SOURCE_PRIORITY = [
    "irs_bmf",
    "propublica",
    "charity_nav",
    "va_facilities",
    "va_vso",
    "nodc",
    "nrd",
]


def merge_all(
    base: pd.DataFrame,
    ein_sources: dict[str, pd.DataFrame],
    non_ein_sources: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Merge all sources into a single DataFrame.

    Args:
        base: IRS BMF base DataFrame (has EINs)
        ein_sources: Dict of source_name → DataFrame for EIN-joinable sources
        non_ein_sources: Dict of source_name → DataFrame for sources without EINs
    """
    logger.info(f"Starting merge with {len(base):,} base records")

    result = coerce_schema(base.copy())

    # Left-join EIN-based sources
    for name, src_df in ein_sources.items():
        if src_df.empty:
            logger.info(f"Skipping empty source: {name}")
            continue

        src_df = coerce_schema(src_df.copy())
        logger.info(f"Merging {name}: {len(src_df):,} records")

        result = _smart_merge_on_ein(result, src_df, name)
        logger.info(f"After {name} merge: {len(result):,} records")

    # Outer-merge non-EIN sources
    for name, src_df in non_ein_sources.items():
        if src_df.empty:
            logger.info(f"Skipping empty source: {name}")
            continue

        src_df = coerce_schema(src_df.copy())
        logger.info(f"Appending {name}: {len(src_df):,} records")

        result = pd.concat([result, src_df], ignore_index=True)
        logger.info(f"After {name} append: {len(result):,} records")

    return result


def _smart_merge_on_ein(
    base: pd.DataFrame, source: pd.DataFrame, source_name: str
) -> pd.DataFrame:
    """Left-join source onto base by EIN, filling blanks without overwriting."""
    if "ein" not in source.columns or source["ein"].isna().all():
        return base

    # Only keep relevant columns from source (those that have data)
    src_cols = ["ein"]
    for col in source.columns:
        if col == "ein":
            continue
        if col in COLUMN_NAMES and source[col].notna().any():
            src_cols.append(col)

    source_slim = source[src_cols].drop_duplicates(subset=["ein"])

    # Merge
    merged = base.merge(source_slim, on="ein", how="left", suffixes=("", f"_{source_name}"))

    # Fill blanks from source columns
    for col in src_cols:
        if col == "ein":
            continue
        src_col = f"{col}_{source_name}"
        if src_col in merged.columns:
            mask = merged[col].isna() | (merged[col] == "")
            merged.loc[mask, col] = merged.loc[mask, src_col]
            merged.drop(columns=[src_col], inplace=True)

    # Merge data_sources
    if f"data_sources_{source_name}" in merged.columns:
        for idx in merged.index:
            existing = merged.at[idx, "data_sources"]
            new_src = merged.at[idx, f"data_sources_{source_name}"]
            if pd.notna(new_src):
                sources = set()
                if pd.notna(existing):
                    sources.update(existing.split(";"))
                sources.update(new_src.split(";"))
                sources.discard("")
                merged.at[idx, "data_sources"] = ";".join(sorted(sources))
        merged.drop(columns=[f"data_sources_{source_name}"], inplace=True)

    # Drop any remaining suffixed columns
    drop_cols = [c for c in merged.columns if c.endswith(f"_{source_name}")]
    if drop_cols:
        merged.drop(columns=drop_cols, inplace=True)

    return merged

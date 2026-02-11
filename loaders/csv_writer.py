"""Final CSV output with confidence scores and summary report."""

import logging
from datetime import datetime

import pandas as pd

from config.schema import (
    COLUMN_NAMES,
    CONFIDENCE_WEIGHTS,
    coerce_schema,
    revenue_to_range,
)
from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)


def calculate_confidence(df: pd.DataFrame) -> pd.Series:
    """Calculate a confidence score (0.0–1.0) per row based on field completeness."""
    scores = pd.Series(0.0, index=df.index, dtype="float64")

    for col, weight in CONFIDENCE_WEIGHTS.items():
        if col in df.columns:
            filled = df[col].notna() & (df[col].astype(str).str.strip() != "")
            scores += filled.astype(float) * weight

    # Normalize to 0-1 (weights should sum to ~1.0 already)
    total_weight = sum(CONFIDENCE_WEIGHTS.values())
    if total_weight > 0:
        scores = scores / total_weight

    return scores.round(3)


def write_csv(df: pd.DataFrame, filename: str = "veteran_org_directory.csv") -> str:
    """Write the final CSV and summary report.

    Returns the path to the CSV file.
    """
    df = coerce_schema(df.copy())

    # Calculate confidence scores
    df["confidence_score"] = calculate_confidence(df)

    # Calculate revenue ranges
    df["annual_revenue_range"] = df["total_revenue"].apply(revenue_to_range)

    # Set record timestamp
    now = datetime.now().isoformat(timespec="seconds")
    df["record_last_updated"] = now

    # Sort by state → name
    df = df.sort_values(["state", "org_name"], na_position="last").reset_index(drop=True)

    # Write UTF-8 CSV with BOM for Excel compatibility
    csv_path = OUTPUT_DIR / filename
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    logger.info(f"Wrote {len(df):,} records to {csv_path}")

    # Generate summary report
    report = _generate_summary(df)
    report_path = OUTPUT_DIR / "summary_report.txt"
    report_path.write_text(report)
    logger.info(f"Summary report: {report_path}")

    return str(csv_path)


def _generate_summary(df: pd.DataFrame) -> str:
    """Generate a text summary report of the directory."""
    lines = [
        "=" * 70,
        "VETERAN ORGANIZATION DIRECTORY — SUMMARY REPORT",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "=" * 70,
        "",
        f"Total organizations: {len(df):,}",
        f"Unique EINs: {df['ein'].dropna().nunique():,}",
        f"Records with EIN: {df['ein'].notna().sum():,}",
        f"Records without EIN: {df['ein'].isna().sum():,}",
        "",
        "── Coverage ──",
        f"States/territories represented: {df['state'].dropna().nunique()}",
        f"Records with phone: {df['phone'].notna().sum():,}",
        f"Records with email: {df['email'].notna().sum():,}",
        f"Records with website: {df['website'].notna().sum():,}",
        f"Records with mission: {df['mission_statement'].notna().sum():,}",
        f"Records with financials: {df['total_revenue'].notna().sum():,}",
        f"Records with CN rating: {df['charity_navigator_rating'].notna().sum():,}",
        f"VA-accredited orgs: {(df['va_accredited'] == 'Yes').sum():,}",
        "",
        "── Confidence Scores ──",
        f"Mean confidence: {df['confidence_score'].mean():.3f}",
        f"Median confidence: {df['confidence_score'].median():.3f}",
        f"High confidence (>0.7): {(df['confidence_score'] > 0.7).sum():,}",
        f"Medium confidence (0.4-0.7): {((df['confidence_score'] >= 0.4) & (df['confidence_score'] <= 0.7)).sum():,}",
        f"Low confidence (<0.4): {(df['confidence_score'] < 0.4).sum():,}",
        "",
        "── By State (top 15) ──",
    ]

    state_counts = df["state"].value_counts().head(15)
    for state, count in state_counts.items():
        lines.append(f"  {state}: {count:,}")

    lines.extend([
        "",
        "── By Organization Type ──",
    ])
    type_counts = df["org_type"].value_counts().head(10)
    for otype, count in type_counts.items():
        lines.append(f"  {otype}: {count:,}")

    lines.extend([
        "",
        "── By Revenue Range ──",
    ])
    rev_counts = df["annual_revenue_range"].value_counts()
    for rev_range, count in rev_counts.items():
        if pd.notna(rev_range):
            lines.append(f"  {rev_range}: {count:,}")

    lines.extend([
        "",
        "── Data Sources ──",
    ])
    all_sources = df["data_sources"].dropna().str.split(";").explode().str.strip()
    source_counts = all_sources[all_sources != ""].value_counts()
    for source, count in source_counts.items():
        lines.append(f"  {source}: {count:,}")

    lines.extend([
        "",
        "=" * 70,
    ])

    return "\n".join(lines)

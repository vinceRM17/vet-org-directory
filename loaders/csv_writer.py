"""Final CSV output with confidence scores and summary report."""

import json
import logging
from datetime import datetime

import pandas as pd

from config.schema import (
    COLUMN_NAMES,
    CONFIDENCE_TIERS,
    CONFIDENCE_WEIGHTS,
    FIELD_GROUPS,
    GRADE_INFO,
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


# Source heuristic: map field group → likely data source
_GROUP_SOURCE_MAP = {
    "identity": "irs_bmf",
    "location": "irs_bmf",
    "classification": "irs_bmf",
    "financials": "propublica",
    "contact": "web_enrichment",
    "ratings": "charity_nav",
    "description": "nrd",
    "social": "web_enrichment",
    "personnel": "propublica",
}


def _row_has(row, col):
    """Check if a row value is non-null and non-empty."""
    val = row.get(col)
    if val is None:
        return False
    try:
        if pd.isna(val):
            return False
    except (ValueError, TypeError):
        pass
    return str(val).strip() != ""


def assign_grade(row) -> str:
    """Assign a letter grade A-F based on what field groups are present."""
    has_name = _row_has(row, "org_name")
    has_ein = _row_has(row, "ein")
    has_address = _row_has(row, "street_address") or (_row_has(row, "city") and _row_has(row, "state"))
    has_financials = _row_has(row, "total_revenue")
    has_ntee = _row_has(row, "ntee_code")
    has_contact = _row_has(row, "phone") or _row_has(row, "email") or _row_has(row, "website")
    has_rating = _row_has(row, "charity_navigator_rating") or (row.get("va_accredited") == "Yes")

    has_identity = has_name and has_ein and has_address

    if has_identity and has_financials and has_contact and has_rating:
        return "A"
    elif has_identity and has_financials and has_ntee:
        return "B"
    elif has_identity and (has_financials or has_ntee):
        return "C"
    elif has_name and has_ein and has_address:
        return "D"
    else:
        return "F"


def calculate_confidence_detail(df: pd.DataFrame) -> pd.Series:
    """Calculate per-field-group breakdown as JSON for each row.

    Returns a Series of JSON strings with structure:
    {
        "grade": "B",
        "groups": {
            "identity": {"filled": 3, "total": 3, "source": "irs_bmf"},
            "financials": {"filled": 2, "total": 4, "source": "propublica"},
            ...
        }
    }
    """
    def _detail_for_row(row):
        groups = {}
        for gkey, gdef in FIELD_GROUPS.items():
            fields = gdef["fields"]
            filled = sum(1 for f in fields if _row_has(row, f))
            # Infer source from data_sources column if available
            source = gdef["source_hint"]
            ds = row.get("data_sources")
            if ds and isinstance(ds, str):
                ds_lower = ds.lower()
                if gkey == "financials" and "propublica" in ds_lower:
                    source = "propublica"
                elif gkey in ("identity", "location", "classification") and "irs_bmf" in ds_lower:
                    source = "irs_bmf"
                elif gkey == "contact" and ("va_vso" in ds_lower or "web" in ds_lower):
                    source = "va_vso" if "va_vso" in ds_lower else "web_enrichment"
                elif gkey == "ratings" and "charity_nav" in ds_lower:
                    source = "charity_nav"

            groups[gkey] = {
                "filled": filled,
                "total": len(fields),
                "source": source,
            }

        grade = assign_grade(row)
        return json.dumps({"grade": grade, "groups": groups})

    return df.apply(_detail_for_row, axis=1)


def write_csv(df: pd.DataFrame, filename: str = "veteran_org_directory.csv") -> str:
    """Write the final CSV and summary report.

    Returns the path to the CSV file.
    """
    df = coerce_schema(df.copy())

    # Calculate confidence scores
    df["confidence_score"] = calculate_confidence(df)

    # Calculate confidence detail and grade
    df["confidence_detail"] = calculate_confidence_detail(df)
    df["confidence_grade"] = df["confidence_detail"].apply(
        lambda x: json.loads(x)["grade"] if pd.notna(x) else "F"
    )

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
        "── Confidence Grades ──",
    ]
    if "confidence_grade" in df.columns:
        grade_counts = df["confidence_grade"].value_counts()
        for g in ("A", "B", "C", "D", "F"):
            cnt = grade_counts.get(g, 0)
            info = GRADE_INFO.get(g, {})
            label = info.get("label", "")
            lines.append(f"  {g} ({label}): {cnt:,}")
    lines.extend([
        "",
        "── By State (top 15) ──",
    ])

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

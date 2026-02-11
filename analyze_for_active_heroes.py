#!/usr/bin/env python3
"""
Active Heroes — Strategic Analysis Views

Generates filtered CSV exports from the veteran org directory to support
Active Heroes' mission in fundraising, partnerships, and awareness.

Usage:
    python3 analyze_for_active_heroes.py [--state KY]

Outputs (in data/output/active_heroes/):
    1. local_partners.csv         — Orgs in Active Heroes' home state (default: KY)
    2. potential_funders.csv       — High-rated, high-revenue orgs (potential grant sources)
    3. peer_network.csv            — Orgs offering mental health / suicide prevention
    4. underserved_gap_analysis.csv — States with fewest orgs per veteran population
    5. board_prospects.csv         — Key personnel at well-run veteran orgs
    6. social_media_partners.csv   — Orgs with active social media for cross-promotion
    7. summary_dashboard.txt       — Overview stats for all views
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

# Active Heroes is based in Kentucky
DEFAULT_STATE = "KY"

# Keywords indicating mental health / suicide prevention focus
MENTAL_HEALTH_KEYWORDS = [
    "suicide", "mental health", "ptsd", "counseling", "therapy",
    "crisis", "wellness", "behavioral health", "brain injury",
    "tbi", "resilience", "recovery", "healing", "trauma",
    "readjustment", "transition", "peer support",
]

# Keywords indicating foundation / funder orgs
FUNDER_KEYWORDS = [
    "foundation", "fund", "trust", "endowment", "community foundation",
    "philanthrop", "grant", "giving",
]

# Approximate veteran population by state (2023 VA estimates, thousands)
# Used for gap analysis
VET_POP_BY_STATE = {
    "CA": 1560, "TX": 1460, "FL": 1430, "PA": 730, "NY": 700,
    "OH": 670, "VA": 650, "NC": 640, "GA": 600, "IL": 560,
    "MI": 530, "AZ": 500, "WA": 490, "TN": 440, "MO": 400,
    "IN": 370, "SC": 370, "AL": 360, "CO": 360, "WI": 340,
    "KY": 290, "MN": 300, "MD": 340, "OR": 290, "OK": 280,
    "LA": 270, "NJ": 310, "AR": 210, "MS": 200, "KS": 190,
    "NV": 200, "IA": 190, "NM": 150, "UT": 130, "CT": 170,
    "NE": 120, "WV": 140, "ID": 120, "ME": 110, "MT": 90,
    "NH": 100, "HI": 100, "SD": 65, "ND": 55, "AK": 70,
    "DE": 70, "RI": 60, "WY": 45, "VT": 42, "DC": 30,
}


def load_directory(csv_path: str) -> pd.DataFrame:
    """Load the main veteran org directory CSV."""
    df = pd.read_csv(csv_path, dtype=str, low_memory=False)
    # Convert numeric columns
    for col in ["total_revenue", "total_expenses", "total_assets", "net_assets",
                 "charity_navigator_rating", "charity_navigator_score",
                 "confidence_score", "num_employees"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def keyword_match(series: pd.Series, keywords: list) -> pd.Series:
    """Check if any keyword appears in the series (case-insensitive)."""
    combined = series.fillna("").str.lower()
    pattern = "|".join(keywords)
    return combined.str.contains(pattern, regex=True, na=False)


def view1_local_partners(df: pd.DataFrame, state: str) -> pd.DataFrame:
    """Orgs in Active Heroes' home state, sorted by confidence score."""
    local = df[df["state"] == state].copy()
    local = local.sort_values("confidence_score", ascending=False)
    return local


def view2_potential_funders(df: pd.DataFrame) -> pd.DataFrame:
    """High-rated, high-revenue orgs that could be grant sources."""
    has_revenue = df["total_revenue"].notna() & (df["total_revenue"] >= 1_000_000)
    has_rating = df["charity_navigator_rating"].notna() & (df["charity_navigator_rating"] >= 3)

    # Also include orgs with funder-like names regardless of rating
    is_funder_name = keyword_match(df["org_name"], FUNDER_KEYWORDS)

    funders = df[
        (has_revenue & has_rating) | (has_revenue & is_funder_name)
    ].copy()

    funders = funders.sort_values("total_revenue", ascending=False)
    return funders


def view3_peer_network(df: pd.DataFrame) -> pd.DataFrame:
    """Orgs offering mental health / suicide prevention / wellness services."""
    # Search across mission, services, name, and categories
    match_mission = keyword_match(df["mission_statement"], MENTAL_HEALTH_KEYWORDS)
    match_services = keyword_match(df["services_offered"], MENTAL_HEALTH_KEYWORDS)
    match_name = keyword_match(df["org_name"], MENTAL_HEALTH_KEYWORDS)
    match_categories = keyword_match(df["service_categories"], MENTAL_HEALTH_KEYWORDS)

    peers = df[match_mission | match_services | match_name | match_categories].copy()
    peers = peers.sort_values("confidence_score", ascending=False)
    return peers


def view4_gap_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """States ranked by orgs-per-veteran ratio (lowest = most underserved)."""
    state_counts = df["state"].value_counts().to_dict()

    rows = []
    for state, vet_pop_k in VET_POP_BY_STATE.items():
        org_count = state_counts.get(state, 0)
        vet_pop = vet_pop_k * 1000
        ratio = org_count / vet_pop * 100000 if vet_pop > 0 else 0
        rows.append({
            "state": state,
            "org_count": org_count,
            "veteran_population": vet_pop,
            "orgs_per_100k_veterans": round(ratio, 1),
        })

    gap = pd.DataFrame(rows)
    gap = gap.sort_values("orgs_per_100k_veterans", ascending=True)
    return gap


def view5_board_prospects(df: pd.DataFrame) -> pd.DataFrame:
    """Key personnel at well-run, well-rated veteran orgs — potential board members/advisors."""
    has_personnel = df["key_personnel"].notna() & (df["key_personnel"] != "")
    well_run = (
        (df["charity_navigator_rating"].notna() & (df["charity_navigator_rating"] >= 3))
        | (df["total_revenue"].notna() & (df["total_revenue"] >= 500_000))
    )

    prospects = df[has_personnel & well_run].copy()
    prospects = prospects[
        ["org_name", "state", "key_personnel", "charity_navigator_rating",
         "total_revenue", "website", "phone", "email"]
    ]
    prospects = prospects.sort_values("total_revenue", ascending=False)
    return prospects


def view6_social_media_partners(df: pd.DataFrame) -> pd.DataFrame:
    """Orgs with active social media presence for cross-promotion."""
    has_social = (
        df["facebook_url"].notna()
        | df["twitter_url"].notna()
        | df["linkedin_url"].notna()
        | df["instagram_url"].notna()
    )

    social_count = (
        df["facebook_url"].notna().astype(int)
        + df["twitter_url"].notna().astype(int)
        + df["linkedin_url"].notna().astype(int)
        + df["instagram_url"].notna().astype(int)
        + df["youtube_url"].notna().astype(int)
    )

    partners = df[has_social].copy()
    partners["social_platform_count"] = social_count[has_social]
    partners = partners.sort_values("social_platform_count", ascending=False)

    cols = [
        "org_name", "state", "website", "facebook_url", "twitter_url",
        "linkedin_url", "instagram_url", "youtube_url",
        "social_platform_count", "total_revenue",
    ]
    return partners[[c for c in cols if c in partners.columns]]


def generate_dashboard(
    df: pd.DataFrame, local: pd.DataFrame, funders: pd.DataFrame,
    peers: pd.DataFrame, gap: pd.DataFrame, board: pd.DataFrame,
    social: pd.DataFrame, state: str,
) -> str:
    """Generate a text summary dashboard."""
    lines = [
        "=" * 70,
        "ACTIVE HEROES — STRATEGIC ANALYSIS DASHBOARD",
        "=" * 70,
        "",
        f"Total orgs in directory: {len(df):,}",
        "",
        f"── 1. Local Partners ({state}) ──",
        f"  Total orgs in {state}: {len(local):,}",
    ]
    if len(local) > 0:
        with_phone = local["phone"].notna().sum()
        with_email = local["email"].notna().sum()
        with_website = local["website"].notna().sum()
        lines.extend([
            f"  With phone: {with_phone:,}",
            f"  With email: {with_email:,}",
            f"  With website: {with_website:,}",
            f"  Top 5 by confidence:",
        ])
        for _, row in local.head(5).iterrows():
            lines.append(f"    - {row['org_name']} ({row.get('city', 'N/A')})")

    lines.extend([
        "",
        "── 2. Potential Funders ──",
        f"  Total prospects: {len(funders):,}",
    ])
    if len(funders) > 0:
        total_rev = funders["total_revenue"].sum()
        lines.append(f"  Combined revenue: ${total_rev:,.0f}")
        lines.append(f"  Top 10 by revenue:")
        for _, row in funders.head(10).iterrows():
            rev = row["total_revenue"]
            name = row["org_name"]
            st = row.get("state", "?")
            lines.append(f"    - {name} ({st}) — ${rev:,.0f}")

    lines.extend([
        "",
        "── 3. Peer Network (Mental Health / Suicide Prevention) ──",
        f"  Total peer orgs: {len(peers):,}",
    ])
    if len(peers) > 0:
        top_states = peers["state"].value_counts().head(5)
        lines.append("  Top states:")
        for st, cnt in top_states.items():
            lines.append(f"    {st}: {cnt}")
        lines.append(f"  Top 5 peers:")
        for _, row in peers.head(5).iterrows():
            lines.append(f"    - {row['org_name']} ({row.get('state', '?')})")

    lines.extend([
        "",
        "── 4. Underserved Areas (Gap Analysis) ──",
        "  Most underserved states (fewest orgs per 100K veterans):",
    ])
    for _, row in gap.head(10).iterrows():
        lines.append(
            f"    {row['state']}: {row['orgs_per_100k_veterans']} orgs/100K vets "
            f"({row['org_count']} orgs, {row['veteran_population']:,} veterans)"
        )

    lines.extend([
        "",
        "── 5. Board / Advisor Prospects ──",
        f"  Total orgs with named leadership: {len(board):,}",
    ])

    lines.extend([
        "",
        "── 6. Social Media Cross-Promotion ──",
        f"  Orgs with social media: {len(social):,}",
    ])
    if len(social) > 0:
        multi = (social["social_platform_count"] >= 3).sum()
        lines.append(f"  Orgs on 3+ platforms: {multi:,}")

    lines.extend([
        "",
        "=" * 70,
        "Files saved to data/output/active_heroes/",
        "=" * 70,
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Active Heroes strategic analysis")
    parser.add_argument(
        "--state", default=DEFAULT_STATE,
        help=f"Home state for local partner view (default: {DEFAULT_STATE})"
    )
    parser.add_argument(
        "--csv", default=None,
        help="Path to veteran org directory CSV (auto-detected if not specified)"
    )
    args = parser.parse_args()

    # Find the CSV
    if args.csv:
        csv_path = args.csv
    else:
        default_path = Path(__file__).parent / "data" / "output" / "veteran_org_directory.csv"
        if not default_path.exists():
            print(f"ERROR: CSV not found at {default_path}")
            print("Run the pipeline first, or specify --csv path")
            sys.exit(1)
        csv_path = str(default_path)

    print(f"Loading directory from {csv_path}...")
    df = load_directory(csv_path)
    print(f"Loaded {len(df):,} organizations")

    # Create output directory
    output_dir = Path(__file__).parent / "data" / "output" / "active_heroes"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate all views
    state = args.state.upper()

    print(f"\n1. Local partners ({state})...")
    local = view1_local_partners(df, state)
    local.to_csv(output_dir / "local_partners.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(local):,} orgs")

    print("2. Potential funders...")
    funders = view2_potential_funders(df)
    funders.to_csv(output_dir / "potential_funders.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(funders):,} prospects")

    print("3. Peer network (mental health / suicide prevention)...")
    peers = view3_peer_network(df)
    peers.to_csv(output_dir / "peer_network.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(peers):,} peer orgs")

    print("4. Gap analysis...")
    gap = view4_gap_analysis(df)
    gap.to_csv(output_dir / "underserved_gap_analysis.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(gap)} states analyzed")

    print("5. Board / advisor prospects...")
    board = view5_board_prospects(df)
    board.to_csv(output_dir / "board_prospects.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(board):,} prospects")

    print("6. Social media partners...")
    social = view6_social_media_partners(df)
    social.to_csv(output_dir / "social_media_partners.csv", index=False, encoding="utf-8-sig")
    print(f"   {len(social):,} orgs with social presence")

    # Generate dashboard
    print("\nGenerating dashboard...")
    dashboard = generate_dashboard(df, local, funders, peers, gap, board, social, state)
    dashboard_path = output_dir / "summary_dashboard.txt"
    dashboard_path.write_text(dashboard)
    print(dashboard)

    print(f"\nAll files saved to: {output_dir}")


if __name__ == "__main__":
    main()

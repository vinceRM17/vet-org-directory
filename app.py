"""
Veteran Organization Directory — Streamlit Dashboard

Interactive search, filter, and explore 77K+ veteran support organizations.
Built for Active Heroes to identify partners, funders, and peer organizations.

Usage:
    streamlit run app.py
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page Config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Veteran Org Directory",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR = Path(__file__).parent / "data" / "output"
CSV_PATH = DATA_DIR / "veteran_org_directory.csv"

# State FIPS for choropleth mapping
STATE_ABBREV_TO_NAME = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming", "DC": "District of Columbia",
}


@st.cache_data
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, dtype=str, low_memory=False)
    for col in ["total_revenue", "total_expenses", "total_assets", "net_assets",
                 "charity_navigator_rating", "charity_navigator_score",
                 "confidence_score", "num_employees"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def format_currency(val):
    if pd.isna(val):
        return "N/A"
    if val >= 1_000_000_000:
        return f"${val / 1_000_000_000:.1f}B"
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    if val >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:.0f}"


# ── Load Data ──────────────────────────────────────────────────────────
if not CSV_PATH.exists():
    st.error(f"Data file not found: {CSV_PATH}")
    st.info("Run `python main.py` first to generate the directory.")
    st.stop()

df = load_data()

# ── Sidebar Filters ────────────────────────────────────────────────────
st.sidebar.title("Filters")

# Search
search_query = st.sidebar.text_input("Search organization name", placeholder="e.g. Wounded Warrior, VFW")

# State filter
all_states = sorted(df["state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("State", all_states, default=[])

# Org type filter
all_org_types = sorted(df["org_type"].dropna().unique().tolist())
selected_org_types = st.sidebar.multiselect("Organization Type", all_org_types, default=[])

# Revenue range
rev_options = ["Any", "Under $50K", "$50K–$500K", "$500K–$1M", "$1M–$10M", "$10M–$100M", "$100M+"]
selected_revenue = st.sidebar.selectbox("Revenue Range", rev_options)

# VA Accredited
va_filter = st.sidebar.selectbox("VA Accredited", ["Any", "Yes", "No"])

# NTEE Code prefix
ntee_input = st.sidebar.text_input("NTEE Code (prefix)", placeholder="e.g. W, W30, P70")

# Confidence score
min_confidence = st.sidebar.slider("Min Confidence Score", 0.0, 1.0, 0.0, 0.05)

# ── Apply Filters ──────────────────────────────────────────────────────
filtered = df.copy()

if search_query:
    mask = filtered["org_name"].str.contains(search_query, case=False, na=False)
    # Also search mission and services
    if "mission_statement" in filtered.columns:
        mask |= filtered["mission_statement"].str.contains(search_query, case=False, na=False)
    if "services_offered" in filtered.columns:
        mask |= filtered["services_offered"].str.contains(search_query, case=False, na=False)
    filtered = filtered[mask]

if selected_states:
    filtered = filtered[filtered["state"].isin(selected_states)]

if selected_org_types:
    filtered = filtered[filtered["org_type"].isin(selected_org_types)]

if selected_revenue != "Any":
    rev_ranges = {
        "Under $50K": (0, 50_000),
        "$50K–$500K": (50_000, 500_000),
        "$500K–$1M": (500_000, 1_000_000),
        "$1M–$10M": (1_000_000, 10_000_000),
        "$10M–$100M": (10_000_000, 100_000_000),
        "$100M+": (100_000_000, float("inf")),
    }
    low, high = rev_ranges[selected_revenue]
    filtered = filtered[
        (filtered["total_revenue"] >= low) & (filtered["total_revenue"] <= high)
    ]

if va_filter == "Yes":
    filtered = filtered[filtered["va_accredited"] == "Yes"]
elif va_filter == "No":
    filtered = filtered[filtered["va_accredited"] != "Yes"]

if ntee_input:
    filtered = filtered[filtered["ntee_code"].str.startswith(ntee_input.upper(), na=False)]

if min_confidence > 0:
    filtered = filtered[filtered["confidence_score"] >= min_confidence]

# ── Main Content ───────────────────────────────────────────────────────
st.title("Veteran Organization Directory")
st.caption(f"Showing {len(filtered):,} of {len(df):,} organizations")

# ── Tab Layout ─────────────────────────────────────────────────────────
tab_overview, tab_explore, tab_map, tab_funders, tab_peers, tab_gaps = st.tabs([
    "Overview", "Explore", "Map", "Potential Funders", "Peer Network", "Gap Analysis"
])

# ── TAB: Overview ──────────────────────────────────────────────────────
with tab_overview:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Organizations", f"{len(filtered):,}")
    col2.metric("States Represented", filtered["state"].nunique())
    col3.metric(
        "Total Revenue",
        format_currency(filtered["total_revenue"].sum())
    )
    col4.metric(
        "VA Accredited",
        f"{(filtered['va_accredited'] == 'Yes').sum():,}"
    )

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("With Financials", f"{filtered['total_revenue'].notna().sum():,}")
    col6.metric("501(c)(19) Orgs", f"{(filtered['org_type'] == '501(c)(19)').sum():,}")
    col7.metric("501(c)(3) Orgs", f"{(filtered['org_type'] == '501(c)(3)').sum():,}")
    col8.metric(
        "Avg Confidence",
        f"{filtered['confidence_score'].mean():.2f}" if len(filtered) > 0 else "N/A"
    )

    st.divider()

    # Org type distribution
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By Organization Type")
        type_counts = filtered["org_type"].value_counts().head(8)
        fig_type = px.pie(
            values=type_counts.values,
            names=type_counts.index,
            hole=0.4,
        )
        fig_type.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig_type, use_container_width=True)

    with c2:
        st.subheader("By Revenue Range")
        rev_counts = filtered["annual_revenue_range"].value_counts()
        # Order the revenue ranges logically
        rev_order = ["$0", "Under $50K", "$50K–$100K", "$100K–$500K",
                      "$500K–$1M", "$1M–$5M", "$5M–$10M", "$10M–$50M",
                      "$50M–$100M", "$100M+"]
        rev_ordered = rev_counts.reindex([r for r in rev_order if r in rev_counts.index]).dropna()
        fig_rev = px.bar(
            x=rev_ordered.index,
            y=rev_ordered.values,
            labels={"x": "Revenue Range", "y": "Count"},
        )
        fig_rev.update_layout(margin=dict(t=20, b=20, l=20, r=20), height=350)
        st.plotly_chart(fig_rev, use_container_width=True)

    # Top states
    st.subheader("Top 15 States")
    state_counts = filtered["state"].value_counts().head(15)
    fig_states = px.bar(
        x=state_counts.index,
        y=state_counts.values,
        labels={"x": "State", "y": "Organizations"},
        color=state_counts.values,
        color_continuous_scale="Blues",
    )
    fig_states.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=350,
        showlegend=False,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig_states, use_container_width=True)


# ── TAB: Explore ───────────────────────────────────────────────────────
with tab_explore:
    st.subheader("Organization Directory")

    display_cols = [
        "org_name", "state", "city", "org_type", "total_revenue",
        "va_accredited", "ntee_code", "phone", "website", "confidence_score",
    ]
    available_cols = [c for c in display_cols if c in filtered.columns]

    # Sort options
    sort_col = st.selectbox(
        "Sort by",
        ["org_name", "total_revenue", "confidence_score", "state"],
        index=0,
    )
    sort_asc = sort_col == "org_name"
    display_df = filtered[available_cols].sort_values(
        sort_col, ascending=sort_asc, na_position="last"
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=500,
        column_config={
            "org_name": st.column_config.TextColumn("Organization", width="large"),
            "total_revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
            "confidence_score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    # Download button
    csv_export = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download filtered results ({len(filtered):,} orgs)",
        data=csv_export,
        file_name="vet_org_filtered.csv",
        mime="text/csv",
    )

    # Org detail expander
    st.divider()
    st.subheader("Organization Detail")
    org_search = st.text_input("Search for a specific org", key="detail_search")
    if org_search:
        matches = filtered[filtered["org_name"].str.contains(org_search, case=False, na=False)]
        if len(matches) > 0:
            selected_org = st.selectbox(
                "Select organization",
                matches["org_name"].tolist()[:20],
            )
            org_row = matches[matches["org_name"] == selected_org].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Identity**")
                st.write(f"**Name:** {org_row.get('org_name', 'N/A')}")
                st.write(f"**EIN:** {org_row.get('ein', 'N/A')}")
                st.write(f"**Type:** {org_row.get('org_type', 'N/A')}")
                st.write(f"**NTEE:** {org_row.get('ntee_code', 'N/A')}")

                st.markdown("**Contact**")
                st.write(f"**Address:** {org_row.get('street_address', '')}, {org_row.get('city', '')}, {org_row.get('state', '')} {org_row.get('zip_code', '')}")
                st.write(f"**Phone:** {org_row.get('phone', 'N/A')}")
                st.write(f"**Email:** {org_row.get('email', 'N/A')}")
                st.write(f"**Website:** {org_row.get('website', 'N/A')}")

            with c2:
                st.markdown("**Financials**")
                st.write(f"**Revenue:** {format_currency(org_row.get('total_revenue'))}")
                st.write(f"**Expenses:** {format_currency(org_row.get('total_expenses'))}")
                st.write(f"**Assets:** {format_currency(org_row.get('total_assets'))}")
                st.write(f"**Net Assets:** {format_currency(org_row.get('net_assets'))}")
                st.write(f"**Employees:** {org_row.get('num_employees', 'N/A')}")

                st.markdown("**Ratings & Status**")
                st.write(f"**VA Accredited:** {org_row.get('va_accredited', 'N/A')}")
                st.write(f"**CN Rating:** {org_row.get('charity_navigator_rating', 'N/A')}")
                st.write(f"**Confidence:** {org_row.get('confidence_score', 'N/A')}")
                st.write(f"**Data Sources:** {org_row.get('data_sources', 'N/A')}")

            if pd.notna(org_row.get("mission_statement")):
                st.markdown("**Mission**")
                st.write(org_row["mission_statement"])

            if pd.notna(org_row.get("key_personnel")):
                st.markdown("**Key Personnel**")
                try:
                    personnel = json.loads(org_row["key_personnel"])
                    for p in personnel[:10]:
                        st.write(f"- {p.get('name', '')} — {p.get('title', '')}")
                except (json.JSONDecodeError, TypeError):
                    st.write(org_row["key_personnel"])
        else:
            st.info("No organizations found matching your search.")


# ── TAB: Map ───────────────────────────────────────────────────────────
with tab_map:
    st.subheader("Organizations by State")

    state_data = filtered["state"].value_counts().reset_index()
    state_data.columns = ["state", "count"]
    state_data["state_name"] = state_data["state"].map(STATE_ABBREV_TO_NAME)

    fig_map = px.choropleth(
        state_data,
        locations="state",
        locationmode="USA-states",
        color="count",
        scope="usa",
        color_continuous_scale="Blues",
        labels={"count": "Organizations", "state": "State"},
        hover_name="state_name",
        hover_data={"count": True, "state": False},
    )
    fig_map.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=500,
        geo=dict(bgcolor="rgba(0,0,0,0)"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # State detail table
    state_summary = filtered.groupby("state").agg(
        org_count=("org_name", "count"),
        total_revenue=("total_revenue", "sum"),
        avg_revenue=("total_revenue", "mean"),
        va_accredited=("va_accredited", lambda x: (x == "Yes").sum()),
        with_financials=("total_revenue", lambda x: x.notna().sum()),
    ).reset_index().sort_values("org_count", ascending=False)

    st.dataframe(
        state_summary,
        use_container_width=True,
        column_config={
            "state": "State",
            "org_count": st.column_config.NumberColumn("Orgs"),
            "total_revenue": st.column_config.NumberColumn("Total Revenue", format="$%d"),
            "avg_revenue": st.column_config.NumberColumn("Avg Revenue", format="$%d"),
            "va_accredited": st.column_config.NumberColumn("VA Accredited"),
            "with_financials": st.column_config.NumberColumn("With Financials"),
        },
    )


# ── TAB: Potential Funders ─────────────────────────────────────────────
with tab_funders:
    st.subheader("Potential Funders for Active Heroes")
    st.caption("Organizations with $1M+ revenue — potential grant sources and partners")

    funder_keywords = ["foundation", "fund", "trust", "endowment", "philanthrop", "grant", "giving"]
    is_funder_name = filtered["org_name"].str.lower().str.contains(
        "|".join(funder_keywords), na=False
    )
    high_revenue = filtered["total_revenue"].notna() & (filtered["total_revenue"] >= 1_000_000)
    funders = filtered[high_revenue].copy()
    funders = funders.sort_values("total_revenue", ascending=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Potential Funders", f"{len(funders):,}")
    col2.metric("Combined Revenue", format_currency(funders["total_revenue"].sum()))
    col3.metric("Avg Revenue", format_currency(funders["total_revenue"].mean()) if len(funders) > 0 else "N/A")

    funder_cols = ["org_name", "state", "city", "total_revenue", "total_assets",
                    "org_type", "ntee_code", "website", "phone"]
    available = [c for c in funder_cols if c in funders.columns]

    st.dataframe(
        funders[available].head(100),
        use_container_width=True,
        height=400,
        column_config={
            "org_name": st.column_config.TextColumn("Organization", width="large"),
            "total_revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
            "total_assets": st.column_config.NumberColumn("Assets", format="$%d"),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    csv_funders = funders[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download funder list ({len(funders):,} orgs)",
        data=csv_funders,
        file_name="potential_funders.csv",
        mime="text/csv",
    )


# ── TAB: Peer Network ─────────────────────────────────────────────────
with tab_peers:
    st.subheader("Peer Network — Mental Health & Suicide Prevention")
    st.caption("Organizations working in veteran mental health, PTSD, crisis support, and wellness")

    mh_keywords = [
        "suicide", "mental health", "ptsd", "counseling", "therapy",
        "crisis", "wellness", "behavioral health", "brain injury",
        "tbi", "resilience", "recovery", "healing", "trauma",
        "readjustment", "transition", "peer support",
    ]
    pattern = "|".join(mh_keywords)

    mh_mask = pd.Series(False, index=filtered.index)
    for col in ["org_name", "mission_statement", "services_offered", "service_categories"]:
        if col in filtered.columns:
            mh_mask |= filtered[col].str.contains(pattern, case=False, na=False)

    peers = filtered[mh_mask].copy()

    col1, col2, col3 = st.columns(3)
    col1.metric("Peer Organizations", f"{len(peers):,}")
    col2.metric("States Represented", peers["state"].nunique() if len(peers) > 0 else 0)
    col3.metric(
        "Combined Revenue",
        format_currency(peers["total_revenue"].sum()) if len(peers) > 0 else "N/A"
    )

    if len(peers) > 0:
        # State distribution
        peer_states = peers["state"].value_counts().head(10)
        fig_peer = px.bar(
            x=peer_states.index,
            y=peer_states.values,
            labels={"x": "State", "y": "Peer Orgs"},
            color=peer_states.values,
            color_continuous_scale="Reds",
        )
        fig_peer.update_layout(
            margin=dict(t=20, b=20), height=300,
            showlegend=False, coloraxis_showscale=False,
        )
        st.plotly_chart(fig_peer, use_container_width=True)

    peer_cols = ["org_name", "state", "city", "total_revenue", "org_type",
                  "mission_statement", "services_offered", "website"]
    available = [c for c in peer_cols if c in peers.columns]
    st.dataframe(
        peers[available].sort_values("total_revenue", ascending=False, na_position="last").head(100),
        use_container_width=True,
        height=400,
        column_config={
            "org_name": st.column_config.TextColumn("Organization", width="large"),
            "total_revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
            "mission_statement": st.column_config.TextColumn("Mission", width="large"),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    csv_peers = peers[available].to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download peer network ({len(peers):,} orgs)",
        data=csv_peers,
        file_name="peer_network.csv",
        mime="text/csv",
    )


# ── TAB: Gap Analysis ─────────────────────────────────────────────────
with tab_gaps:
    st.subheader("Underserved Areas — Gap Analysis")
    st.caption("States with the fewest veteran organizations relative to veteran population")

    vet_pop = {
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

    state_counts = filtered["state"].value_counts().to_dict()
    gap_rows = []
    for state, pop_k in vet_pop.items():
        org_count = state_counts.get(state, 0)
        pop = pop_k * 1000
        ratio = org_count / pop * 100_000 if pop > 0 else 0
        gap_rows.append({
            "State": state,
            "State Name": STATE_ABBREV_TO_NAME.get(state, state),
            "Organizations": org_count,
            "Veteran Population": pop,
            "Orgs per 100K Veterans": round(ratio, 1),
        })

    gap_df = pd.DataFrame(gap_rows).sort_values("Orgs per 100K Veterans")

    # Choropleth - lower ratio = more red (underserved)
    fig_gap = px.choropleth(
        gap_df,
        locations="State",
        locationmode="USA-states",
        color="Orgs per 100K Veterans",
        scope="usa",
        color_continuous_scale="RdYlGn",
        hover_name="State Name",
        hover_data={"Organizations": True, "Veteran Population": True},
    )
    fig_gap.update_layout(
        margin=dict(t=20, b=20, l=20, r=20),
        height=500,
    )
    st.plotly_chart(fig_gap, use_container_width=True)

    st.subheader("Most Underserved States")
    st.dataframe(
        gap_df.head(15),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Veteran Population": st.column_config.NumberColumn(format="%d"),
        },
    )

    st.subheader("Best Served States")
    st.dataframe(
        gap_df.tail(10).sort_values("Orgs per 100K Veterans", ascending=False),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Veteran Population": st.column_config.NumberColumn(format="%d"),
        },
    )


# ── Sidebar Footer ────────────────────────────────────────────────────
st.sidebar.divider()
st.sidebar.caption(
    f"Data: {len(df):,} organizations from IRS BMF, ProPublica, VA OGC, NRD\n\n"
    f"Last updated: {df['data_freshness_date'].dropna().max() if 'data_freshness_date' in df.columns else 'N/A'}"
)

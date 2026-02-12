"""
Veteran Organization Directory — Streamlit Dashboard

Interactive search, filter, and explore 80K+ veteran support organizations.
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

from config.schema import (
    CONFIDENCE_TIERS,
    FIELD_GROUPS,
    GRADE_INFO,
    GRADE_OPTIONS,
)

# ── Page Config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Veteran Org Directory",
    page_icon="🎖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color Tokens ──────────────────────────────────────────────────────
NAVY = "#1B3A5C"
SLATE = "#2D3748"
BLUE = "#3182CE"
RED_ACCENT = "#C53030"
GREEN = "#2F855A"
AMBER = "#D69E2E"

CHART_COLORS = [
    "#1B3A5C", "#2C5282", "#3182CE", "#63B3ED",
    "#C53030", "#FC8181", "#2F855A", "#68D391",
]

# ── CSS Design System ─────────────────────────────────────────────────
st.markdown("""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Navy sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1b3a5c 0%, #15304d 100%) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] { color: #d0dbe6 !important; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h1,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h2,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3,
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong { color: #ffffff !important; }
    section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #a0b8cf !important; }
    section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.15) !important; }
    section[data-testid="stSidebar"] label { color: #d0dbe6 !important; }

    /* Hero header */
    .hero-header {
        background: linear-gradient(135deg, #1b3a5c 0%, #2C5282 50%, #3182CE 100%);
        color: white; padding: 2rem 2.5rem; border-radius: 1rem;
        margin-bottom: 1.5rem; position: relative; overflow: hidden;
    }
    .hero-header::before {
        content: ''; position: absolute; top: -40px; right: -40px;
        width: 160px; height: 160px; border-radius: 50%;
        background: rgba(255,255,255,0.06); pointer-events: none;
    }
    .hero-header h1 { color: #fff !important; margin-bottom: 0.25rem; font-size: 2rem; position: relative; }
    .hero-header p { color: #d4e8f0; margin: 0; font-size: 1.05rem; position: relative; }

    /* Custom metric card */
    .metric-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 0.75rem;
        padding: 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.10); }
    .metric-card .mc-icon { font-size: 1.5rem; margin-bottom: 0.25rem; }
    .metric-card .mc-value { font-size: 1.8rem; font-weight: 800; color: #2D3748; line-height: 1.2; }
    .metric-card .mc-label { font-size: 0.85rem; color: #718096; margin-top: 0.15rem; }

    /* Grade badges */
    .grade-badge {
        display: inline-block; padding: 3px 14px; border-radius: 12px;
        font-size: 0.82rem; font-weight: 700; color: white; white-space: nowrap;
    }
    .grade-A { background: #2F855A; }
    .grade-B { background: #2C5282; }
    .grade-C { background: #D69E2E; }
    .grade-D { background: #DD6B20; }
    .grade-F { background: #C53030; }

    /* Source tags */
    .source-tag {
        display: inline-block; background: #EDF2F7; color: #4A5568;
        border: 1px solid #E2E8F0; padding: 1px 8px; border-radius: 8px;
        font-size: 0.72rem; font-weight: 600; margin-right: 3px;
    }

    /* Confidence breakdown grid */
    .conf-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; margin: 0.75rem 0; }
    .conf-group-card {
        background: white; border: 1px solid #E2E8F0; border-radius: 0.5rem;
        padding: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .conf-group-card .cg-header { display: flex; justify-content: space-between; margin-bottom: 0.35rem; }
    .conf-group-card .cg-label { font-size: 0.78rem; font-weight: 600; color: #2D3748; }
    .conf-group-card .cg-count { font-size: 0.72rem; color: #718096; }
    .conf-group-card .cg-bar { height: 6px; background: #EDF2F7; border-radius: 3px; overflow: hidden; margin-bottom: 0.25rem; }
    .conf-group-card .cg-bar-fill { height: 100%; border-radius: 3px; }

    /* Headers */
    h1 { color: #1b3a5c; }
    h2 { color: #2D3748; }
    h3 { color: #2C5282; }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        border-bottom-color: #1B3A5C !important; color: #1B3A5C !important;
    }

    /* Default metrics */
    div[data-testid="stMetric"] {
        background: white; border: 1px solid #E2E8F0; border-radius: 0.75rem;
        padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }
</style>""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────────────────

def metric_card(label, value, icon="", border_color=NAVY):
    return (
        f'<div class="metric-card" style="border-top: 3px solid {border_color};">'
        f'<div class="mc-icon">{icon}</div>'
        f'<div class="mc-value">{value}</div>'
        f'<div class="mc-label">{label}</div>'
        f'</div>'
    )


def style_chart(fig, height=400):
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, sans-serif", color="#2D3748"),
        colorway=CHART_COLORS,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
    )
    return fig


def grade_badge_html(grade, show_label=True):
    info = GRADE_INFO.get(grade, GRADE_INFO.get("F", {}))
    label_text = f" {info.get('label', '')}" if show_label else ""
    return f'<span class="grade-badge grade-{grade}">{grade}{label_text}</span>'


def render_confidence_breakdown(detail_json):
    """Render 3-column grid of field-group cards from a confidence_detail JSON string."""
    try:
        detail = json.loads(detail_json) if isinstance(detail_json, str) else detail_json
    except (json.JSONDecodeError, TypeError):
        return ""

    groups = detail.get("groups", {})
    cards = ""
    for gkey, gdata in groups.items():
        gdef = FIELD_GROUPS.get(gkey, {})
        filled = gdata.get("filled", 0)
        total = gdata.get("total", 1)
        pct = round(filled / total * 100) if total > 0 else 0
        bar_color = "#2F855A" if pct >= 80 else "#3182CE" if pct >= 40 else "#D69E2E" if pct > 0 else "#E2E8F0"
        icon = gdef.get("icon", "")
        label = gdef.get("label", gkey)
        source = gdata.get("source", "")

        cards += (
            f'<div class="conf-group-card">'
            f'<div class="cg-header">'
            f'<span class="cg-label">{icon} {label}</span>'
            f'<span class="cg-count">{filled}/{total}</span>'
            f'</div>'
            f'<div class="cg-bar"><div class="cg-bar-fill" '
            f'style="width:{pct}%; background:{bar_color};"></div></div>'
            f'<span class="source-tag">{source}</span>'
            f'</div>'
        )
    return f'<div class="conf-grid">{cards}</div>'


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


# ── Data ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data" / "output"
CSV_PATH = DATA_DIR / "veteran_org_directory.csv"

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


@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, dtype=str, low_memory=False)
    for col in ["total_revenue", "total_expenses", "total_assets", "net_assets",
                 "charity_navigator_rating", "charity_navigator_score",
                 "confidence_score", "num_employees"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


# ── Load Data ─────────────────────────────────────────────────────────
if not CSV_PATH.exists():
    st.error(f"Data file not found: {CSV_PATH}")
    st.info("Run `python main.py` first to generate the directory.")
    st.stop()

df = load_data()

# ── Sidebar ───────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<div style="text-align:center; padding: 0.5rem 0 1rem 0;">'
    '<h2 style="margin-bottom: 0;">🎖️ Veteran Org<br>Directory</h2>'
    '<p style="font-size: 0.85rem;">Active Heroes &bull; Shepherdsville, KY</p>'
    '</div>',
    unsafe_allow_html=True,
)
st.sidebar.divider()

# Search (expanded: name, city, mission, services, service_categories, eligibility)
search_query = st.sidebar.text_input("Search", placeholder="e.g. Wounded Warrior, Louisville, housing")

# Grade-based filter (primary)
selected_grades = st.sidebar.multiselect(
    "Data Quality Grade",
    options=GRADE_OPTIONS,
    default=[],
)
_required_grade_letters = [g.split(" - ")[0] for g in selected_grades]

# Grade distribution summary
if "confidence_grade" in df.columns:
    grade_counts = df["confidence_grade"].value_counts()
    dist_parts = []
    for t in CONFIDENCE_TIERS:
        g = t["grade"]
        cnt = grade_counts.get(g, 0)
        dist_parts.append(f"<strong>{g}</strong>: {cnt:,}")
    st.sidebar.markdown(
        '<div style="font-size:0.78rem; line-height:1.6; color:#a0b8cf;">'
        + " &bull; ".join(dist_parts) + "</div>",
        unsafe_allow_html=True,
    )

# State filter
all_states = sorted(df["state"].dropna().unique().tolist())
selected_states = st.sidebar.multiselect("State", all_states, default=[])

# City search
city_query = st.sidebar.text_input("City", placeholder="e.g. Louisville, San Diego")

# ZIP code search
zip_query = st.sidebar.text_input("ZIP Code (prefix)", placeholder="e.g. 40165, 921")

# Service categories
_all_categories = set()
if "service_categories" in df.columns:
    for val in df["service_categories"].dropna().unique():
        for cat in str(val).split(";"):
            cat = cat.strip()
            if cat:
                _all_categories.add(cat)
all_categories = sorted(_all_categories)
selected_categories = st.sidebar.multiselect("Service Categories", all_categories, default=[]) if all_categories else []

# Advanced filters in expander
with st.sidebar.expander("Advanced Filters"):
    all_org_types = sorted(df["org_type"].dropna().unique().tolist())
    selected_org_types = st.sidebar.multiselect("Organization Type", all_org_types, default=[])

    rev_options = ["Any", "Under $50K", "$50K–$500K", "$500K–$1M", "$1M–$10M", "$10M–$100M", "$100M+"]
    selected_revenue = st.selectbox("Revenue Range", rev_options)

    va_filter = st.selectbox("VA Accredited", ["Any", "Yes", "No"])

    ntee_input = st.text_input("NTEE Code (prefix)", placeholder="e.g. W, W30, P70")

    has_contact = st.checkbox("Has contact info (phone, email, or website)")

    emp_options = ["Any", "1–10", "11–50", "51–200", "201–1000", "1000+"]
    selected_employees = st.selectbox("Employee Count", emp_options)

    min_confidence = st.slider("Min Confidence Score", 0.0, 1.0, 0.0, 0.05)

# Sidebar footer
st.sidebar.divider()
st.sidebar.markdown(
    '<div style="text-align:center; font-size:0.72rem; color:#5a7a96;">'
    'Built for Active Heroes<br>Shepherdsville, KY</div>',
    unsafe_allow_html=True,
)

# ── Apply Filters ─────────────────────────────────────────────────────
filtered = df.copy()

if search_query:
    mask = filtered["org_name"].str.contains(search_query, case=False, na=False)
    for col in ["city", "mission_statement", "services_offered", "service_categories", "eligibility_requirements"]:
        if col in filtered.columns:
            mask |= filtered[col].str.contains(search_query, case=False, na=False)
    filtered = filtered[mask]

if _required_grade_letters and "confidence_grade" in filtered.columns:
    filtered = filtered[filtered["confidence_grade"].isin(_required_grade_letters)]

if selected_states:
    filtered = filtered[filtered["state"].isin(selected_states)]

if city_query:
    filtered = filtered[filtered["city"].str.contains(city_query, case=False, na=False)]

if zip_query:
    filtered = filtered[filtered["zip_code"].str.startswith(zip_query, na=False)]

if selected_categories:
    cat_mask = pd.Series(False, index=filtered.index)
    for cat in selected_categories:
        cat_mask |= filtered["service_categories"].str.contains(cat, case=False, na=False)
    filtered = filtered[cat_mask]

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

if has_contact:
    contact_mask = pd.Series(False, index=filtered.index)
    for col in ["phone", "email", "website"]:
        if col in filtered.columns:
            contact_mask |= filtered[col].notna() & (filtered[col].str.strip() != "")
    filtered = filtered[contact_mask]

if selected_employees != "Any":
    emp_ranges = {
        "1–10": (1, 10),
        "11–50": (11, 50),
        "51–200": (51, 200),
        "201–1000": (201, 1000),
        "1000+": (1000, float("inf")),
    }
    emp_low, emp_high = emp_ranges[selected_employees]
    filtered = filtered[
        filtered["num_employees"].notna()
        & (filtered["num_employees"] >= emp_low)
        & (filtered["num_employees"] <= emp_high)
    ]

if min_confidence > 0:
    filtered = filtered[filtered["confidence_score"] >= min_confidence]

# ── Hero Header ───────────────────────────────────────────────────────
avg_conf = filtered["confidence_score"].mean() if len(filtered) > 0 else 0
st.markdown(f"""
<div class="hero-header">
    <h1>Veteran Organization Directory</h1>
    <p>Built for Active Heroes &bull; {len(filtered):,} of {len(df):,} organizations</p>
</div>
""", unsafe_allow_html=True)

# ── Tab Layout ────────────────────────────────────────────────────────
tab_overview, tab_explore, tab_map, tab_funders, tab_peers, tab_gaps = st.tabs([
    "Overview", "Explore", "Map", "Potential Funders", "Peer Network", "Gap Analysis"
])

# ── TAB: Overview ─────────────────────────────────────────────────────
with tab_overview:
    # KPI metric cards
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(metric_card("Total Organizations", f"{len(filtered):,}", "🏢", NAVY), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("States Represented", str(filtered["state"].nunique()), "🗺️", "#2C5282"), unsafe_allow_html=True)
    with col3:
        st.markdown(metric_card("Total Revenue", format_currency(filtered["total_revenue"].sum()), "💰", GREEN), unsafe_allow_html=True)
    with col4:
        st.markdown(metric_card("VA Accredited", f"{(filtered['va_accredited'] == 'Yes').sum():,}", "🛡️", "#D69E2E"), unsafe_allow_html=True)

    col5, col6, col7, col8 = st.columns(4)
    with col5:
        st.markdown(metric_card("With Financials", f"{filtered['total_revenue'].notna().sum():,}", "📊", "#2C5282"), unsafe_allow_html=True)
    with col6:
        st.markdown(metric_card("501(c)(19) Orgs", f"{(filtered['org_type'] == '501(c)(19)').sum():,}", "🎖️", NAVY), unsafe_allow_html=True)
    with col7:
        st.markdown(metric_card("501(c)(3) Orgs", f"{(filtered['org_type'] == '501(c)(3)').sum():,}", "🏛️", GREEN), unsafe_allow_html=True)
    with col8:
        avg_str = f"{avg_conf:.2f}" if len(filtered) > 0 else "N/A"
        st.markdown(metric_card("Avg Confidence", avg_str, "📈", "#D69E2E"), unsafe_allow_html=True)

    st.divider()

    # Grade distribution chart
    if "confidence_grade" in filtered.columns:
        st.subheader("Confidence Grade Distribution")
        grade_cts = filtered["confidence_grade"].value_counts()
        grade_df = pd.DataFrame([
            {"Grade": f"{g} - {GRADE_INFO[g]['label']}", "Count": int(grade_cts.get(g, 0))}
            for g in ("A", "B", "C", "D", "F")
        ])
        fig_grade = px.bar(
            grade_df, x="Grade", y="Count",
            color="Grade",
            color_discrete_map={
                f"{g} - {GRADE_INFO[g]['label']}": GRADE_INFO[g]["color"]
                for g in ("A", "B", "C", "D", "F")
            },
            title="Organizations by Data Quality Grade",
        )
        fig_grade.update_layout(showlegend=False)
        style_chart(fig_grade, height=300)
        st.plotly_chart(fig_grade, use_container_width=True)

    # Org type + Revenue charts
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By Organization Type")
        type_counts = filtered["org_type"].value_counts().head(8)
        fig_type = px.pie(values=type_counts.values, names=type_counts.index, hole=0.4)
        style_chart(fig_type, height=350)
        st.plotly_chart(fig_type, use_container_width=True)

    with c2:
        st.subheader("By Revenue Range")
        rev_counts = filtered["annual_revenue_range"].value_counts()
        rev_order = ["$0", "Under $50K", "$50K–$100K", "$100K–$500K",
                      "$500K–$1M", "$1M–$5M", "$5M–$10M", "$10M–$50M",
                      "$50M–$100M", "$100M+"]
        rev_ordered = rev_counts.reindex([r for r in rev_order if r in rev_counts.index]).dropna()
        if len(rev_ordered) > 0:
            rev_df = pd.DataFrame({"Revenue Range": rev_ordered.index, "Count": rev_ordered.values})
            fig_rev = px.bar(rev_df, x="Revenue Range", y="Count")
            style_chart(fig_rev, height=350)
            st.plotly_chart(fig_rev, use_container_width=True)
        else:
            st.info("No revenue data available for current filter.")

    # Top states
    st.subheader("Top 15 States")
    state_counts = filtered["state"].value_counts().head(15)
    state_df = pd.DataFrame({"State": state_counts.index, "Organizations": state_counts.values})
    fig_states = px.bar(state_df, x="State", y="Organizations")
    style_chart(fig_states, height=350)
    st.plotly_chart(fig_states, use_container_width=True)


# ── TAB: Explore ──────────────────────────────────────────────────────
with tab_explore:
    st.subheader("Organization Directory")

    display_cols = [
        "org_name", "state", "city", "org_type", "total_revenue",
        "va_accredited", "ntee_code", "phone", "website",
        "confidence_score",
    ]
    if "confidence_grade" in filtered.columns:
        display_cols.insert(-1, "confidence_grade")
    available_cols = [c for c in display_cols if c in filtered.columns]

    sort_col = st.selectbox("Sort by", ["org_name", "total_revenue", "confidence_score", "state"], index=0)
    sort_asc = sort_col == "org_name"
    display_df = filtered[available_cols].sort_values(sort_col, ascending=sort_asc, na_position="last")

    st.dataframe(
        display_df,
        use_container_width=True,
        height=500,
        column_config={
            "org_name": st.column_config.TextColumn("Organization", width="large"),
            "total_revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
            "confidence_score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1),
            "confidence_grade": st.column_config.TextColumn("Grade", width="small"),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    csv_export = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download filtered results ({len(filtered):,} orgs)",
        data=csv_export,
        file_name="vet_org_filtered.csv",
        mime="text/csv",
    )

    # Organization Detail
    st.divider()
    st.subheader("Organization Detail")
    org_search = st.text_input("Search for a specific org", key="detail_search")
    if org_search:
        matches = filtered[filtered["org_name"].str.contains(org_search, case=False, na=False)]
        if len(matches) > 0:
            selected_org = st.selectbox("Select organization", matches["org_name"].tolist()[:20])
            org_row = matches[matches["org_name"] == selected_org].iloc[0]

            # Header with grade badge
            grade = org_row.get("confidence_grade", "F") if pd.notna(org_row.get("confidence_grade")) else "F"
            va_badge = ""
            if org_row.get("va_accredited") == "Yes":
                va_badge = ' <span class="grade-badge" style="background:#D69E2E;">VA Accredited</span>'
            st.markdown(
                f'<h2 style="margin-bottom:0.25rem;">{org_row.get("org_name", "N/A")}</h2>'
                f'{grade_badge_html(grade)} {va_badge}'
                f' <span class="source-tag">{org_row.get("data_sources", "")}</span>',
                unsafe_allow_html=True,
            )

            # Confidence breakdown grid
            detail_json = org_row.get("confidence_detail")
            if pd.notna(detail_json):
                st.markdown(render_confidence_breakdown(detail_json), unsafe_allow_html=True)

            # Three-column content
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(
                    f'<div class="metric-card" style="border-top:3px solid {NAVY};">'
                    f'<h4 style="color:{NAVY};">Identity & Location</h4>'
                    f'<p><strong>EIN:</strong> {org_row.get("ein", "N/A")}</p>'
                    f'<p><strong>Type:</strong> {org_row.get("org_type", "N/A")}</p>'
                    f'<p><strong>NTEE:</strong> {org_row.get("ntee_code", "N/A")}</p>'
                    f'<p><strong>Address:</strong> {org_row.get("street_address", "")}, '
                    f'{org_row.get("city", "")}, {org_row.get("state", "")} {org_row.get("zip_code", "")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f'<div class="metric-card" style="border-top:3px solid {GREEN};">'
                    f'<h4 style="color:{GREEN};">Financials</h4>'
                    f'<p><strong>Revenue:</strong> {format_currency(org_row.get("total_revenue"))}</p>'
                    f'<p><strong>Expenses:</strong> {format_currency(org_row.get("total_expenses"))}</p>'
                    f'<p><strong>Assets:</strong> {format_currency(org_row.get("total_assets"))}</p>'
                    f'<p><strong>Net Assets:</strong> {format_currency(org_row.get("net_assets"))}</p>'
                    f'<p><strong>Employees:</strong> {org_row.get("num_employees", "N/A")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            with c3:
                phone_val = org_row.get("phone", "N/A")
                email_val = org_row.get("email", "N/A")
                website_val = org_row.get("website", "N/A")
                website_link = f'<a href="{website_val}" target="_blank">{website_val}</a>' if pd.notna(website_val) and website_val != "N/A" else "N/A"
                st.markdown(
                    f'<div class="metric-card" style="border-top:3px solid {BLUE};">'
                    f'<h4 style="color:{BLUE};">Contact & Social</h4>'
                    f'<p><strong>Phone:</strong> {phone_val if pd.notna(phone_val) else "N/A"}</p>'
                    f'<p><strong>Email:</strong> {email_val if pd.notna(email_val) else "N/A"}</p>'
                    f'<p><strong>Website:</strong> {website_link}</p>'
                    f'<p><strong>CN Rating:</strong> {org_row.get("charity_navigator_rating", "N/A")}</p>'
                    f'<p><strong>Confidence:</strong> {org_row.get("confidence_score", "N/A")}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Mission statement
            if pd.notna(org_row.get("mission_statement")):
                st.markdown(
                    f'<div class="metric-card" style="border-top:3px solid #D69E2E; margin-top:0.75rem;">'
                    f'<h4 style="color:#D69E2E;">Mission</h4>'
                    f'<p>{org_row["mission_statement"]}</p>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            # Personnel
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


# ── TAB: Map ──────────────────────────────────────────────────────────
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
        color_continuous_scale=[[0, "#EDF2F7"], [0.5, "#3182CE"], [1, "#1B3A5C"]],
        labels={"count": "Organizations", "state": "State"},
        hover_name="state_name",
        hover_data={"count": True, "state": False},
    )
    style_chart(fig_map, height=500)
    fig_map.update_layout(geo=dict(bgcolor="rgba(0,0,0,0)"))
    st.plotly_chart(fig_map, use_container_width=True)

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


# ── TAB: Potential Funders ────────────────────────────────────────────
with tab_funders:
    st.subheader("Potential Funders for Active Heroes")
    st.caption("Organizations with $1M+ revenue — potential grant sources and partners")

    high_revenue = filtered["total_revenue"].notna() & (filtered["total_revenue"] >= 1_000_000)
    funders = filtered[high_revenue].copy().sort_values("total_revenue", ascending=False)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(metric_card("Potential Funders", f"{len(funders):,}", "💰", NAVY), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("Combined Revenue", format_currency(funders["total_revenue"].sum()), "📊", GREEN), unsafe_allow_html=True)
    with col3:
        avg_rev = format_currency(funders["total_revenue"].mean()) if len(funders) > 0 else "N/A"
        st.markdown(metric_card("Avg Revenue", avg_rev, "📈", "#2C5282"), unsafe_allow_html=True)

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


# ── TAB: Peer Network ────────────────────────────────────────────────
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
    with col1:
        st.markdown(metric_card("Peer Organizations", f"{len(peers):,}", "🤝", NAVY), unsafe_allow_html=True)
    with col2:
        st.markdown(metric_card("States Represented", str(peers["state"].nunique()) if len(peers) > 0 else "0", "🗺️", "#2C5282"), unsafe_allow_html=True)
    with col3:
        peer_rev = format_currency(peers["total_revenue"].sum()) if len(peers) > 0 else "N/A"
        st.markdown(metric_card("Combined Revenue", peer_rev, "💰", GREEN), unsafe_allow_html=True)

    if len(peers) > 0:
        peer_states = peers["state"].value_counts().head(10)
        peer_state_df = pd.DataFrame({"State": peer_states.index, "Peer Orgs": peer_states.values})
        fig_peer = px.bar(peer_state_df, x="State", y="Peer Orgs")
        fig_peer.update_traces(marker_color=CHART_COLORS[:len(peer_state_df)])
        style_chart(fig_peer, height=300)
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


# ── TAB: Gap Analysis ────────────────────────────────────────────────
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

    fig_gap = px.choropleth(
        gap_df,
        locations="State",
        locationmode="USA-states",
        color="Orgs per 100K Veterans",
        scope="usa",
        color_continuous_scale=[[0, "#C53030"], [0.5, "#D69E2E"], [1, "#2F855A"]],
        hover_name="State Name",
        hover_data={"Organizations": True, "Veteran Population": True},
    )
    style_chart(fig_gap, height=500)
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

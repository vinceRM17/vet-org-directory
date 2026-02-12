"""
Veteran Organization Directory — Streamlit Dashboard

Interactive search, filter, and explore 80K+ veteran support organizations.
Built for Active Heroes to identify partners, funders, and peer organizations.

Usage:
    streamlit run app.py
"""

import json
from pathlib import Path
from urllib.parse import quote_plus

import numpy as np
import pandas as pd
import pgeocode
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config.schema import (
    CONFIDENCE_TIERS,
    FIELD_GROUPS,
    GRADE_INFO,
    GRADE_OPTIONS,
    LEGACY_GRADE_MAP,
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
    .grade-Enriched { background: #2F855A; }
    .grade-Baseline { background: #2C5282; }
    .grade-Partial { background: #D69E2E; }

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

    /* Detail page */
    .detail-section {
        background: white; border: 1px solid #E2E8F0; border-radius: 0.75rem;
        padding: 1.25rem; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 1rem;
    }
    .detail-section h4 { margin-top: 0; margin-bottom: 0.75rem; }
    .detail-section p { margin: 0.3rem 0; font-size: 0.92rem; line-height: 1.5; }
    .detail-na { color: #A0AEC0; font-style: italic; }

    .social-pill {
        display: inline-block; background: #EBF4FF; color: #2C5282;
        border: 1px solid #BEE3F8; padding: 4px 12px; border-radius: 16px;
        font-size: 0.82rem; font-weight: 600; margin: 3px 4px 3px 0;
        text-decoration: none; transition: background 0.15s;
    }
    .social-pill:hover { background: #BEE3F8; }

    .personnel-item {
        padding: 0.4rem 0; border-bottom: 1px solid #F7FAFC;
    }
    .personnel-item:last-child { border-bottom: none; }
    .personnel-name { font-weight: 600; color: #2D3748; }
    .personnel-title { color: #718096; font-size: 0.88rem; }
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
    info = GRADE_INFO.get(grade, GRADE_INFO.get("Partial", {}))
    return f'<span class="grade-badge grade-{grade}">{info.get("label", grade)}</span>'


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


def detail_row(label, value, is_link=False):
    """Render a single label: value row, with gray 'Not available' for missing data."""
    if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
        return f'<p><strong>{label}:</strong> <span class="detail-na">Not available</span></p>'
    if is_link and isinstance(value, str) and value.startswith(("http://", "https://")):
        return f'<p><strong>{label}:</strong> <a href="{value}" target="_blank">{value}</a></p>'
    return f'<p><strong>{label}:</strong> {value}</p>'


def has_data(row, fields):
    """Return True if any field in the list has a non-null, non-empty value."""
    for f in fields:
        val = row.get(f)
        if pd.notna(val) and (not isinstance(val, str) or val.strip() != ""):
            return True
    return False


def google_search_url(org_name):
    """Construct a Google search URL for an organization name."""
    return f"https://www.google.com/search?q={quote_plus(org_name)}"


def render_org_detail(df, ein):
    """Render a full-page detail view for the organization matching the given EIN."""
    matches = df[df["ein"] == ein]
    if len(matches) == 0:
        st.warning("Organization not found.")
        if st.button("Back to Directory"):
            st.session_state.pop("selected_org_ein", None)
            st.rerun()
        return

    row = matches.iloc[0]

    # ── Back button ──
    if st.button("← Back to Directory"):
        st.session_state.pop("selected_org_ein", None)
        st.rerun()

    # ── Hero header ──
    org_name = row.get("org_name", "Unknown Organization")
    grade = row.get("confidence_grade", "Partial") if pd.notna(row.get("confidence_grade")) else "Partial"
    va_badge = ""
    if row.get("va_accredited") == "Yes":
        va_badge = ' <span class="grade-badge" style="background:#D69E2E;">VA Accredited</span>'
    org_type_tag = ""
    if pd.notna(row.get("org_type")):
        org_type_tag = f' <span class="source-tag" style="font-size:0.82rem;">{row["org_type"]}</span>'
    sources_tag = ""
    if pd.notna(row.get("data_sources")):
        for src in str(row["data_sources"]).split(","):
            sources_tag += f' <span class="source-tag">{src.strip()}</span>'

    st.markdown(
        f'<div class="hero-header">'
        f'<h1>{org_name}</h1>'
        f'<p>{grade_badge_html(grade)}{va_badge}{org_type_tag}{sources_tag}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Confidence breakdown ──
    detail_json = row.get("confidence_detail")
    if pd.notna(detail_json):
        st.markdown(render_confidence_breakdown(detail_json), unsafe_allow_html=True)

    # ── Identity / Location / Classification ──
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid {NAVY};">'
            f'<h4 style="color:{NAVY};">Identity</h4>'
            f'{detail_row("EIN", row.get("ein"))}'
            f'{detail_row("Organization Name", row.get("org_name"))}'
            f'{detail_row("Ruling Date", row.get("ruling_date"))}'
            f'{detail_row("Subsection", row.get("subsection"))}'
            f'{detail_row("Affiliation", row.get("affiliation"))}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c2:
        address_parts = [
            str(row.get("street_address", "")) if pd.notna(row.get("street_address")) else "",
            str(row.get("city", "")) if pd.notna(row.get("city")) else "",
            str(row.get("state", "")) if pd.notna(row.get("state")) else "",
            str(row.get("zip_code", "")) if pd.notna(row.get("zip_code")) else "",
        ]
        address = ", ".join(p for p in address_parts if p).strip(", ")
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid {BLUE};">'
            f'<h4 style="color:{BLUE};">Location</h4>'
            f'{detail_row("Address", address if address else None)}'
            f'{detail_row("City", row.get("city"))}'
            f'{detail_row("State", row.get("state"))}'
            f'{detail_row("ZIP Code", row.get("zip_code"))}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid {GREEN};">'
            f'<h4 style="color:{GREEN};">Classification</h4>'
            f'{detail_row("Org Type", row.get("org_type"))}'
            f'{detail_row("NTEE Code", row.get("ntee_code"))}'
            f'{detail_row("NTEE Description", row.get("ntee_description"))}'
            f'{detail_row("Foundation Code", row.get("foundation_code"))}'
            f'{detail_row("Activity Code", row.get("activity_code"))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Financials (conditional) ──
    fin_fields = ["total_revenue", "total_expenses", "total_assets", "net_assets",
                   "total_liabilities", "num_employees", "num_volunteers", "annual_revenue_range"]
    if has_data(row, fin_fields):
        st.markdown(f'<h3 style="margin-top:1.5rem;">Financials</h3>', unsafe_allow_html=True)
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            st.markdown(metric_card("Revenue", format_currency(row.get("total_revenue")), "💰", GREEN), unsafe_allow_html=True)
        with fc2:
            st.markdown(metric_card("Expenses", format_currency(row.get("total_expenses")), "📉", RED_ACCENT), unsafe_allow_html=True)
        with fc3:
            st.markdown(metric_card("Assets", format_currency(row.get("total_assets")), "🏦", NAVY), unsafe_allow_html=True)
        with fc4:
            st.markdown(metric_card("Net Assets", format_currency(row.get("net_assets")), "📊", BLUE), unsafe_allow_html=True)

        fc5, fc6, fc7, fc8 = st.columns(4)
        with fc5:
            liab = format_currency(row.get("total_liabilities"))
            st.markdown(metric_card("Liabilities", liab, "📋", AMBER), unsafe_allow_html=True)
        with fc6:
            emp = row.get("num_employees")
            emp_str = f"{int(emp):,}" if pd.notna(emp) else "N/A"
            st.markdown(metric_card("Employees", emp_str, "👥", SLATE), unsafe_allow_html=True)
        with fc7:
            vol = row.get("num_volunteers")
            vol_str = f"{int(vol):,}" if pd.notna(vol) else "N/A"
            st.markdown(metric_card("Volunteers", vol_str, "🙋", GREEN), unsafe_allow_html=True)
        with fc8:
            rev_range = row.get("annual_revenue_range")
            st.markdown(metric_card("Revenue Range", rev_range if pd.notna(rev_range) else "N/A", "📈", BLUE), unsafe_allow_html=True)

    # ── Contact & Web (always shown — Google search fallback for website) ──
    website_val = row.get("website")
    if pd.notna(website_val) and isinstance(website_val, str) and website_val.strip():
        website_html = f'<p><strong>Website:</strong> <a href="{website_val}" target="_blank">{website_val}</a></p>'
    else:
        search_url = google_search_url(org_name)
        website_html = (
            f'<p><strong>Website:</strong> '
            f'<a href="{search_url}" target="_blank">Search online for {org_name}</a></p>'
        )
    st.markdown(
        f'<div class="detail-section" style="border-top:3px solid {BLUE}; margin-top:1rem;">'
        f'<h4 style="color:{BLUE};">Contact & Web</h4>'
        f'{detail_row("Phone", row.get("phone"))}'
        f'{detail_row("Email", row.get("email"))}'
        f'{website_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Mission & Services (conditional) ──
    mission_fields = ["mission_statement", "services_offered", "service_categories",
                       "eligibility_requirements", "service_area", "year_founded"]
    if has_data(row, mission_fields):
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid #D69E2E; margin-top:1rem;">'
            f'<h4 style="color:#D69E2E;">Mission & Services</h4>'
            f'{detail_row("Mission", row.get("mission_statement"))}'
            f'{detail_row("Services Offered", row.get("services_offered"))}'
            f'{detail_row("Service Categories", row.get("service_categories"))}'
            f'{detail_row("Eligibility", row.get("eligibility_requirements"))}'
            f'{detail_row("Service Area", row.get("service_area"))}'
            f'{detail_row("Year Founded", row.get("year_founded"))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Ratings & Accreditation (conditional) ──
    rating_fields = ["charity_navigator_rating", "charity_navigator_score",
                      "cn_alert_level", "va_accredited", "va_accreditation_details"]
    if has_data(row, rating_fields):
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid {NAVY}; margin-top:1rem;">'
            f'<h4 style="color:{NAVY};">Ratings & Accreditation</h4>'
            f'{detail_row("CN Rating", row.get("charity_navigator_rating"))}'
            f'{detail_row("CN Score", row.get("charity_navigator_score"))}'
            f'{detail_row("CN Alert Level", row.get("cn_alert_level"))}'
            f'{detail_row("VA Accredited", row.get("va_accredited"))}'
            f'{detail_row("VA Details", row.get("va_accreditation_details"))}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Social Media (conditional) ──
    social_fields = ["facebook_url", "twitter_url", "linkedin_url", "instagram_url", "youtube_url"]
    if has_data(row, social_fields):
        social_html = '<div class="detail-section" style="border-top:3px solid #4299E1; margin-top:1rem;">'
        social_html += '<h4 style="color:#4299E1;">Social Media</h4><div>'
        social_labels = {
            "facebook_url": "Facebook", "twitter_url": "Twitter",
            "linkedin_url": "LinkedIn", "instagram_url": "Instagram",
            "youtube_url": "YouTube",
        }
        for field, label in social_labels.items():
            url = row.get(field)
            if pd.notna(url) and isinstance(url, str) and url.strip():
                social_html += f'<a class="social-pill" href="{url}" target="_blank">{label}</a>'
        social_html += '</div></div>'
        st.markdown(social_html, unsafe_allow_html=True)

    # ── Personnel (conditional) ──
    has_personnel = has_data(row, ["key_personnel", "board_members"])
    if has_personnel:
        st.markdown(
            f'<div class="detail-section" style="border-top:3px solid {SLATE}; margin-top:1rem;">'
            f'<h4 style="color:{SLATE};">Personnel</h4>',
            unsafe_allow_html=True,
        )
        # Key personnel (JSON)
        kp = row.get("key_personnel")
        if pd.notna(kp) and str(kp).strip():
            personnel_html = "<strong>Key Personnel</strong>"
            try:
                people = json.loads(kp) if isinstance(kp, str) else kp
                for p in people[:15]:
                    name = p.get("name", "")
                    title = p.get("title", "")
                    personnel_html += (
                        f'<div class="personnel-item">'
                        f'<span class="personnel-name">{name}</span>'
                        f'{f" — <span class=personnel-title>{title}</span>" if title else ""}'
                        f'</div>'
                    )
            except (json.JSONDecodeError, TypeError):
                personnel_html += f'<p>{kp}</p>'
            st.markdown(personnel_html, unsafe_allow_html=True)

        # Board members (semicolon-separated)
        bm = row.get("board_members")
        if pd.notna(bm) and str(bm).strip():
            members = [m.strip() for m in str(bm).split(";") if m.strip()]
            if members:
                board_html = "<strong>Board Members</strong>"
                for m in members[:20]:
                    board_html += f'<div class="personnel-item"><span class="personnel-name">{m}</span></div>'
                st.markdown(board_html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # ── Metadata footer ──
    conf_score = row.get("confidence_score")
    conf_str = f"{conf_score:.2f}" if pd.notna(conf_score) else "N/A"
    freshness = row.get("data_freshness_date", "")
    freshness_str = freshness if pd.notna(freshness) else "N/A"
    sources_str = row.get("data_sources", "")
    sources_str = sources_str if pd.notna(sources_str) else "N/A"

    st.markdown(
        f'<div style="margin-top:2rem; padding:1rem; background:#F7FAFC; border-radius:0.5rem; '
        f'font-size:0.82rem; color:#718096; border:1px solid #E2E8F0;">'
        f'<strong>Data Sources:</strong> {sources_str} &nbsp;&bull;&nbsp; '
        f'<strong>Confidence Score:</strong> {conf_str} &nbsp;&bull;&nbsp; '
        f'<strong>Grade:</strong> {grade} &nbsp;&bull;&nbsp; '
        f'<strong>Freshness:</strong> {freshness_str}'
        f'</div>',
        unsafe_allow_html=True,
    )


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

US_TERRITORIES = {
    "PR": "Puerto Rico", "VI": "U.S. Virgin Islands",
    "GU": "Guam", "AS": "American Samoa",
}

MILITARY_MAIL = {
    "AE": "Armed Forces Europe/Middle East/Africa",
    "AP": "Armed Forces Pacific",
}

# All 50 states + DC (for counting "states" accurately)
US_STATE_CODES = set(STATE_ABBREV_TO_NAME.keys())

# Merge territories and military into the name lookup for display
STATE_ABBREV_TO_NAME.update(US_TERRITORIES)
STATE_ABBREV_TO_NAME.update(MILITARY_MAIL)

# Approximate lat/lng centroids for US states, territories, and military mail codes
STATE_CENTROIDS = {
    "AL": (32.8, -86.8), "AK": (64.2, -152.5), "AZ": (34.3, -111.7),
    "AR": (34.8, -92.2), "CA": (37.2, -119.5), "CO": (39.0, -105.5),
    "CT": (41.6, -72.7), "DE": (39.0, -75.5), "FL": (28.6, -82.4),
    "GA": (33.0, -83.5), "HI": (20.5, -157.5), "ID": (44.4, -114.6),
    "IL": (40.0, -89.2), "IN": (39.8, -86.3), "IA": (42.0, -93.5),
    "KS": (38.5, -98.3), "KY": (37.8, -85.3), "LA": (31.1, -92.0),
    "ME": (45.4, -69.2), "MD": (39.0, -76.8), "MA": (42.3, -71.8),
    "MI": (44.3, -85.4), "MN": (46.3, -94.3), "MS": (32.7, -89.7),
    "MO": (38.4, -92.5), "MT": (47.1, -109.6), "NE": (41.5, -99.8),
    "NV": (39.3, -117.0), "NH": (43.7, -71.6), "NJ": (40.1, -74.7),
    "NM": (34.5, -106.0), "NY": (42.9, -75.5), "NC": (35.6, -79.8),
    "ND": (47.4, -100.5), "OH": (40.4, -82.8), "OK": (35.6, -97.5),
    "OR": (44.0, -120.5), "PA": (40.9, -77.8), "RI": (41.7, -71.5),
    "SC": (34.0, -81.0), "SD": (44.4, -100.2), "TN": (35.9, -86.4),
    "TX": (31.5, -99.4), "UT": (39.3, -111.7), "VT": (44.1, -72.6),
    "VA": (37.5, -78.9), "WA": (47.4, -120.7), "WV": (38.6, -80.6),
    "WI": (44.6, -89.8), "WY": (43.0, -107.6), "DC": (38.9, -77.0),
    "PR": (18.2, -66.5), "VI": (18.3, -64.9), "GU": (13.4, 144.8),
    "AS": (-14.3, -170.7), "AE": (50.1, 8.7), "AP": (35.7, 139.7),
}

# Approximate bounding boxes: (lat_min, lat_max, lon_min, lon_max)
STATE_BOUNDS = {
    "AL": (30.2, 35.0, -88.5, -84.9), "AK": (51.2, 71.4, -179.1, -130.0),
    "AZ": (31.3, 37.0, -114.8, -109.0), "AR": (33.0, 36.5, -94.6, -89.6),
    "CA": (32.5, 42.0, -124.4, -114.1), "CO": (37.0, 41.0, -109.1, -102.0),
    "CT": (41.0, 42.1, -73.7, -71.8), "DE": (38.5, 39.8, -75.8, -75.0),
    "FL": (24.5, 31.0, -87.6, -80.0), "GA": (30.4, 35.0, -85.6, -80.8),
    "HI": (18.9, 22.2, -160.2, -154.8), "ID": (42.0, 49.0, -117.2, -111.0),
    "IL": (37.0, 42.5, -91.5, -87.5), "IN": (37.8, 41.8, -88.1, -84.8),
    "IA": (40.4, 43.5, -96.6, -90.1), "KS": (37.0, 40.0, -102.1, -94.6),
    "KY": (36.5, 39.1, -89.6, -82.0), "LA": (29.0, 33.0, -94.0, -89.0),
    "ME": (43.1, 47.5, -71.1, -67.0), "MD": (38.0, 39.7, -79.5, -75.0),
    "MA": (41.2, 42.9, -73.5, -69.9), "MI": (41.7, 48.3, -90.4, -82.4),
    "MN": (43.5, 49.4, -97.2, -89.5), "MS": (30.2, 35.0, -91.7, -88.1),
    "MO": (36.0, 40.6, -95.8, -89.1), "MT": (44.4, 49.0, -116.1, -104.0),
    "NE": (40.0, 43.0, -104.1, -95.3), "NV": (35.0, 42.0, -120.0, -114.0),
    "NH": (42.7, 45.3, -72.6, -70.7), "NJ": (38.9, 41.4, -75.6, -73.9),
    "NM": (31.3, 37.0, -109.1, -103.0), "NY": (40.5, 45.0, -79.8, -71.9),
    "NC": (33.8, 36.6, -84.3, -75.5), "ND": (45.9, 49.0, -104.1, -96.6),
    "OH": (38.4, 42.0, -84.8, -80.5), "OK": (33.6, 37.0, -103.0, -94.4),
    "OR": (42.0, 46.3, -124.6, -116.5), "PA": (39.7, 42.3, -80.5, -75.0),
    "RI": (41.1, 42.0, -71.9, -71.1), "SC": (32.0, 35.2, -83.4, -78.5),
    "SD": (42.5, 46.0, -104.1, -96.4), "TN": (35.0, 36.7, -90.3, -81.6),
    "TX": (25.8, 36.5, -106.6, -93.5), "UT": (37.0, 42.0, -114.1, -109.0),
    "VT": (42.7, 45.0, -73.4, -71.5), "VA": (36.5, 39.5, -83.7, -75.2),
    "WA": (45.5, 49.0, -124.8, -116.9), "WV": (37.2, 40.6, -82.6, -77.7),
    "WI": (42.5, 47.1, -92.9, -86.8), "WY": (41.0, 45.0, -111.1, -104.1),
    "DC": (38.8, 39.0, -77.1, -76.9),
    "PR": (17.9, 18.5, -67.3, -65.6), "VI": (17.7, 18.4, -65.1, -64.6),
    "GU": (13.2, 13.7, 144.6, 145.0), "AS": (-14.4, -14.2, -170.8, -170.5),
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


@st.cache_data(ttl=3600)
def geocode_zips(zip_series: pd.Series) -> pd.DataFrame:
    """Batch geocode 5-digit ZIP codes → lat/lng using pgeocode."""
    zips_5 = zip_series.str[:5]
    unique_zips = zips_5.dropna().unique()
    nomi = pgeocode.Nominatim("US")
    lookup = nomi.query_postal_code(unique_zips)
    lookup = lookup[["postal_code", "latitude", "longitude"]].dropna()
    lookup = lookup.rename(columns={"postal_code": "zip5"})
    # Merge back to original series index
    mapping = pd.DataFrame({"zip5": zips_5})
    result = mapping.merge(lookup, on="zip5", how="left")
    return result[["latitude", "longitude"]]


# ── Load Data ─────────────────────────────────────────────────────────
if not CSV_PATH.exists():
    st.error(f"Data file not found: {CSV_PATH}")
    st.info("Run `python main.py` first to generate the directory.")
    st.stop()

df = load_data()

# Geocode ZIP codes for map positioning
geo = geocode_zips(df["zip_code"])
df["lat"] = geo["latitude"].values
df["lng"] = geo["longitude"].values

# Remap legacy A-F grades to 3-tier display grades
if "confidence_grade" in df.columns:
    df["confidence_grade"] = df["confidence_grade"].map(LEGACY_GRADE_MAP).fillna("Partial")

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

# Data tier filter (primary)
selected_grades = st.sidebar.multiselect(
    "Data Tier",
    options=GRADE_OPTIONS,
    default=[],
)

# Tier distribution summary
if "confidence_grade" in df.columns:
    grade_counts = df["confidence_grade"].value_counts()
    dist_parts = []
    for t in CONFIDENCE_TIERS:
        g = t["grade"]
        cnt = grade_counts.get(g, 0)
        color = t["color"]
        dist_parts.append(f'<span style="color:{color};"><strong>{g}</strong></span>: {cnt:,}')
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

if selected_grades and "confidence_grade" in filtered.columns:
    filtered = filtered[filtered["confidence_grade"].isin(selected_grades)]

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

# ── Page Routing: Detail Page vs Tab Layout ──────────────────────────
if st.session_state.get("selected_org_ein"):
    render_org_detail(df, st.session_state["selected_org_ein"])
    st.stop()

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
        _all_regions = filtered["state"].dropna().unique()
        _n_states = sum(1 for s in _all_regions if s in US_STATE_CODES)
        _n_territories = sum(1 for s in _all_regions if s in US_TERRITORIES)
        _n_military = sum(1 for s in _all_regions if s in MILITARY_MAIL)
        _extra = _n_territories + _n_military
        _val = f"{_n_states} + {_extra}" if _extra else str(_n_states)
        _label_parts = ["States"]
        if _n_territories:
            _label_parts.append(f"{_n_territories} Territories")
        if _n_military:
            _label_parts.append(f"{_n_military} Military")
        st.markdown(metric_card(" · ".join(_label_parts), _val, "🗺️", "#2C5282"), unsafe_allow_html=True)
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

    # Data tier distribution chart
    if "confidence_grade" in filtered.columns:
        st.subheader("Data Tier Distribution")
        tier_order = [t["grade"] for t in CONFIDENCE_TIERS]
        grade_cts = filtered["confidence_grade"].value_counts()
        grade_df = pd.DataFrame([
            {
                "Tier": g,
                "Count": int(grade_cts.get(g, 0)),
                "Description": GRADE_INFO[g]["description"],
            }
            for g in tier_order
        ])
        fig_grade = px.bar(
            grade_df, x="Tier", y="Count",
            color="Tier",
            color_discrete_map={t["grade"]: t["color"] for t in CONFIDENCE_TIERS},
            title="Organizations by Data Tier",
            hover_data={"Description": True},
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

    # Interactive state map
    st.subheader("Organizations by State")
    st.caption("Hover for state details. Click a state to explore its organizations in the Map tab.")
    overview_state_data = filtered.groupby("state").agg(
        org_count=("org_name", "count"),
        total_revenue=("total_revenue", "sum"),
        va_accredited=("va_accredited", lambda x: (x == "Yes").sum()),
    ).reset_index()
    overview_state_data["state_name"] = overview_state_data["state"].map(STATE_ABBREV_TO_NAME)
    overview_state_data["hover_text"] = overview_state_data.apply(
        lambda r: (
            f"<b>{r['state_name']}</b><br>"
            f"Organizations: {int(r['org_count']):,}<br>"
            f"Total Revenue: {format_currency(r['total_revenue'])}<br>"
            f"VA Accredited: {int(r['va_accredited']):,}"
        ),
        axis=1,
    )
    fig_overview_map = go.Figure(go.Choropleth(
        locations=overview_state_data["state"],
        z=overview_state_data["org_count"],
        locationmode="USA-states",
        colorscale=[[0, "#EDF2F7"], [0.5, "#3182CE"], [1, "#1B3A5C"]],
        text=overview_state_data["hover_text"],
        hoverinfo="text",
        colorbar_title="Orgs",
        marker_line_color="white",
        marker_line_width=1.5,
    ))
    fig_overview_map.update_layout(
        geo=dict(scope="usa", bgcolor="rgba(0,0,0,0)", showlakes=True, lakecolor="white"),
        margin=dict(l=0, r=0, t=0, b=0),
        height=420,
    )
    overview_map_event = st.plotly_chart(
        fig_overview_map, use_container_width=True,
        on_select="rerun", key="overview_choro",
    )
    # Click state on overview → jump to Map tab drill-down
    if overview_map_event and overview_map_event.selection and overview_map_event.selection.points:
        clicked_st = overview_map_event.selection.points[0].get("location")
        if clicked_st:
            st.session_state["map_focused_state"] = clicked_st
            st.info(f"Selected **{STATE_ABBREV_TO_NAME.get(clicked_st, clicked_st)}** — switch to the **Map** tab to explore organizations.")


# ── TAB: Explore ──────────────────────────────────────────────────────
with tab_explore:
    st.subheader("Organization Directory")

    display_cols = [
        "ein", "org_name", "state", "city", "org_type", "total_revenue",
        "va_accredited", "ntee_code", "phone", "website",
        "confidence_score",
    ]
    if "confidence_grade" in filtered.columns:
        display_cols.insert(-1, "confidence_grade")
    available_cols = [c for c in display_cols if c in filtered.columns]

    sort_col = st.selectbox("Sort by", ["org_name", "total_revenue", "confidence_score", "state"], index=0)
    sort_asc = sort_col == "org_name"
    display_df = filtered[available_cols].sort_values(sort_col, ascending=sort_asc, na_position="last")

    st.caption("Select rows to compare organizations, then click an org name to view its full profile")
    event = st.dataframe(
        display_df,
        use_container_width=True,
        height=500,
        on_select="rerun",
        selection_mode="multi-row",
        column_config={
            "ein": st.column_config.TextColumn("EIN", width="small"),
            "org_name": st.column_config.TextColumn("Organization", width="large"),
            "total_revenue": st.column_config.NumberColumn("Revenue", format="$%d"),
            "confidence_score": st.column_config.ProgressColumn("Confidence", min_value=0, max_value=1),
            "confidence_grade": st.column_config.TextColumn("Data Tier", width="small"),
            "website": st.column_config.LinkColumn("Website"),
        },
    )

    # ── Selected Organizations — Comparison Section ──
    if event and event.selection and event.selection.rows:
        selected_rows = event.selection.rows
        st.divider()
        st.subheader(f"Selected Organizations ({len(selected_rows)})")

        for idx in selected_rows:
            org = display_df.iloc[idx]
            org_ein = org.get("ein", "")
            org_name = org.get("org_name", "Unknown")
            grade = org.get("confidence_grade", "Partial") if pd.notna(org.get("confidence_grade")) else "Partial"
            city = org.get("city", "") if pd.notna(org.get("city")) else ""
            state = org.get("state", "") if pd.notna(org.get("state")) else ""
            org_type = org.get("org_type", "") if pd.notna(org.get("org_type")) else ""
            revenue = format_currency(org.get("total_revenue"))
            location = f"{city}, {state}".strip(", ")

            col_btn, col_info = st.columns([1, 3])
            with col_btn:
                if st.button(f"**{org_name}**", key=f"nav_{org_ein}", use_container_width=True):
                    st.session_state["selected_org_ein"] = org_ein
                    st.rerun()
            with col_info:
                st.markdown(
                    f'{grade_badge_html(grade)} &nbsp; {location} · {org_type} · Revenue: {revenue}',
                    unsafe_allow_html=True,
                )

    csv_export = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download filtered results ({len(filtered):,} orgs)",
        data=csv_export,
        file_name="vet_org_filtered.csv",
        mime="text/csv",
    )

    # Organization Search → View Full Profile
    st.divider()
    st.subheader("Search for an Organization")
    org_search = st.text_input("Search by name", key="detail_search")
    if org_search:
        matches = filtered[filtered["org_name"].str.contains(org_search, case=False, na=False)]
        if len(matches) > 0:
            selected_org = st.selectbox("Select organization", matches["org_name"].tolist()[:20])
            org_row = matches[matches["org_name"] == selected_org].iloc[0]

            # Brief preview
            grade = org_row.get("confidence_grade", "Partial") if pd.notna(org_row.get("confidence_grade")) else "Partial"
            st.markdown(
                f'{grade_badge_html(grade)} **{selected_org}** — '
                f'{org_row.get("city", "")} {org_row.get("state", "")} · '
                f'{org_row.get("org_type", "")}',
                unsafe_allow_html=True,
            )

            if st.button("View Full Profile", key="view_profile_btn"):
                st.session_state["selected_org_ein"] = org_row.get("ein")
                st.rerun()
        else:
            st.info("No organizations found matching your search.")


# ── TAB: Map ──────────────────────────────────────────────────────────
with tab_map:
    # Initialize map state
    if "map_focused_state" not in st.session_state:
        st.session_state["map_focused_state"] = None

    focused_state = st.session_state.get("map_focused_state")

    if focused_state is None:
        # ── National Choropleth View ──
        st.subheader("Organizations by State")
        st.caption("Hover over a state to see summary data. Click a state to drill down and explore individual organizations.")

        # Build state summary for hover + table
        state_summary = filtered.groupby("state").agg(
            org_count=("org_name", "count"),
            total_revenue=("total_revenue", "sum"),
            avg_revenue=("total_revenue", "mean"),
            va_accredited=("va_accredited", lambda x: (x == "Yes").sum()),
            with_financials=("total_revenue", lambda x: x.notna().sum()),
        ).reset_index().sort_values("org_count", ascending=False)
        state_summary["state_name"] = state_summary["state"].map(STATE_ABBREV_TO_NAME)

        # Rich hover text
        state_summary["hover_text"] = state_summary.apply(
            lambda r: (
                f"<b>{r['state_name']}</b><br>"
                f"Organizations: {int(r['org_count']):,}<br>"
                f"Total Revenue: {format_currency(r['total_revenue'])}<br>"
                f"VA Accredited: {int(r['va_accredited']):,}<br>"
                f"With Financials: {int(r['with_financials']):,}<br>"
                f"<i>Click to explore →</i>"
            ),
            axis=1,
        )

        fig_map = go.Figure(go.Choropleth(
            locations=state_summary["state"],
            z=state_summary["org_count"],
            locationmode="USA-states",
            colorscale=[[0, "#EDF2F7"], [0.5, "#3182CE"], [1, "#1B3A5C"]],
            text=state_summary["hover_text"],
            hoverinfo="text",
            colorbar_title="Orgs",
            marker_line_color="white",
            marker_line_width=1.5,
        ))
        fig_map.update_layout(
            geo=dict(
                scope="usa",
                bgcolor="rgba(0,0,0,0)",
                showlakes=True, lakecolor="white",
            ),
            margin=dict(l=0, r=0, t=0, b=0),
            height=500,
        )

        choro_event = st.plotly_chart(
            fig_map, use_container_width=True,
            on_select="rerun", key="choro_map",
        )

        # Handle state click on choropleth
        if choro_event and choro_event.selection and choro_event.selection.points:
            clicked_loc = choro_event.selection.points[0].get("location")
            if clicked_loc:
                st.session_state["map_focused_state"] = clicked_loc
                st.rerun()

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

    else:
        # ── Zoomed-In State View ──
        state_name = STATE_ABBREV_TO_NAME.get(focused_state, focused_state)
        state_orgs = filtered[filtered["state"] == focused_state].copy()

        if st.button("← Back to National Map"):
            st.session_state["map_focused_state"] = None
            st.rerun()

        st.subheader(f"{state_name} — {len(state_orgs):,} Organizations")

        if focused_state in STATE_CENTROIDS and len(state_orgs) > 0:
            # KPI row for this state
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.markdown(metric_card("Organizations", f"{len(state_orgs):,}", "🏢", NAVY), unsafe_allow_html=True)
            with sc2:
                st.markdown(metric_card("Total Revenue", format_currency(state_orgs["total_revenue"].sum()), "💰", GREEN), unsafe_allow_html=True)
            with sc3:
                va_cnt = (state_orgs["va_accredited"] == "Yes").sum()
                st.markdown(metric_card("VA Accredited", f"{va_cnt:,}", "🛡️", AMBER), unsafe_allow_html=True)
            with sc4:
                enriched_cnt = (state_orgs["confidence_grade"] == "Enriched").sum()
                st.markdown(metric_card("Enriched Data", f"{enriched_cnt:,}", "📊", BLUE), unsafe_allow_html=True)

            # Cap for performance
            MAP_POINT_LIMIT = 5000
            plot_orgs = state_orgs
            if len(plot_orgs) > MAP_POINT_LIMIT:
                st.info(f"Showing {MAP_POINT_LIMIT:,} of {len(state_orgs):,} orgs. Use sidebar filters to narrow.")
                plot_orgs = plot_orgs.head(MAP_POINT_LIMIT)

            # Use real geocoded lat/lng; drop orgs without coordinates
            plot_orgs = plot_orgs.dropna(subset=["lat", "lng"]).copy()
            if len(plot_orgs) == 0:
                st.info("No geocoded locations available for this state.")
                if st.button("← Back to National Map", key="back_nogeo"):
                    st.session_state["map_focused_state"] = None
                    st.rerun()

            # Compute bounding box from actual data points
            lat_min, lat_max = plot_orgs["lat"].min(), plot_orgs["lat"].max()
            lon_min, lon_max = plot_orgs["lng"].min(), plot_orgs["lng"].max()
            # Fall back to state bounds if data is too tight (e.g. single point)
            if lat_max - lat_min < 0.5 or lon_max - lon_min < 0.5:
                bounds = STATE_BOUNDS.get(focused_state)
                if bounds:
                    lat_min, lat_max, lon_min, lon_max = bounds

            plot_orgs["hover_label"] = plot_orgs.apply(
                lambda r: (
                    f"<b>{r.get('org_name', 'N/A')}</b><br>"
                    f"{r.get('city', '')} {r.get('state', '')}<br>"
                    f"Type: {r.get('org_type', 'N/A')}<br>"
                    f"Revenue: {format_currency(r.get('total_revenue'))}<br>"
                    f"Tier: {r.get('confidence_grade', 'N/A')}"
                ),
                axis=1,
            )

            # Color by data tier
            tier_colors = {"Enriched": "#2F855A", "Baseline": "#2C5282", "Partial": "#D69E2E"}
            plot_orgs["dot_color"] = plot_orgs["confidence_grade"].map(tier_colors).fillna("#718096")

            # Compute center and zoom from bounding box
            center_lat = (lat_min + lat_max) / 2
            center_lon = (lon_min + lon_max) / 2
            lat_span = lat_max - lat_min
            lon_span = lon_max - lon_min
            max_span = max(lat_span, lon_span)
            # Approximate mapbox zoom from span
            if max_span > 15:
                zoom = 4
            elif max_span > 8:
                zoom = 5
            elif max_span > 4:
                zoom = 6
            elif max_span > 2:
                zoom = 7
            elif max_span > 1:
                zoom = 8
            else:
                zoom = 9

            fig_state = go.Figure()
            fig_state.add_trace(go.Scattermapbox(
                lat=plot_orgs["lat"],
                lon=plot_orgs["lng"],
                text=plot_orgs["hover_label"],
                hoverinfo="text",
                marker=dict(
                    size=9,
                    color=plot_orgs["dot_color"],
                    opacity=0.75,
                ),
            ))
            fig_state.update_layout(
                mapbox=dict(
                    style="carto-positron",
                    center=dict(lat=center_lat, lon=center_lon),
                    zoom=zoom,
                ),
                margin=dict(l=0, r=0, t=0, b=0),
                height=550,
            )

            state_map_event = st.plotly_chart(
                fig_state, use_container_width=True,
                on_select="rerun", key="state_org_map",
            )

            # Handle dot click — show org detail card
            if state_map_event and state_map_event.selection and state_map_event.selection.points:
                pt = state_map_event.selection.points[0]
                pt_idx = pt.get("point_index")
                if pt_idx is not None and pt_idx < len(plot_orgs):
                    org = plot_orgs.iloc[pt_idx]
                    o_ein = org.get("ein", "")
                    o_name = org.get("org_name", "Unknown")
                    o_city = org.get("city", "") if pd.notna(org.get("city")) else ""
                    o_state = org.get("state", "") if pd.notna(org.get("state")) else ""
                    o_type = org.get("org_type", "") if pd.notna(org.get("org_type")) else ""
                    o_rev = format_currency(org.get("total_revenue"))
                    o_grade = org.get("confidence_grade", "Partial") if pd.notna(org.get("confidence_grade")) else "Partial"
                    o_phone = org.get("phone", "") if pd.notna(org.get("phone")) else ""
                    o_email = org.get("email", "") if pd.notna(org.get("email")) else ""
                    o_website = org.get("website", "") if pd.notna(org.get("website")) else ""
                    search_url = google_search_url(o_name)
                    web_html = f'<a href="{o_website}" target="_blank">{o_website}</a>' if o_website else f'<a href="{search_url}" target="_blank">Search online</a>'

                    st.markdown(
                        f'<div class="detail-section" style="border-top:3px solid {NAVY};">'
                        f'<h4 style="color:{NAVY};">{o_name}</h4>'
                        f'<p>{grade_badge_html(o_grade)} &nbsp; '
                        f'{o_city}, {o_state} · {o_type} · Revenue: {o_rev}</p>'
                        f'{detail_row("EIN", o_ein)}'
                        f'{detail_row("Phone", o_phone if o_phone else None)}'
                        f'{detail_row("Email", o_email if o_email else None)}'
                        f'<p><strong>Website:</strong> {web_html}</p>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(f"View Full Profile — {o_name}", key="map_view_profile"):
                        st.session_state["selected_org_ein"] = o_ein
                        st.rerun()

            # Tier legend
            st.markdown(
                '<div style="font-size:0.82rem; color:#718096; margin-top:0.5rem;">'
                '<span style="color:#2F855A;">●</span> Enriched &nbsp; '
                '<span style="color:#2C5282;">●</span> Baseline &nbsp; '
                '<span style="color:#D69E2E;">●</span> Partial &nbsp; '
                '· Positions approximate (state-level)</div>',
                unsafe_allow_html=True,
            )
        else:
            st.info("No organizations found for this state with current filters.")
            if st.button("← Back to National Map", key="back_empty"):
                st.session_state["map_focused_state"] = None
                st.rerun()


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

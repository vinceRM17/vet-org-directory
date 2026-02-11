# Veteran Org Directory — Data Enrichment

## What This Is

A data enrichment initiative for the Veteran Organization Directory — an 80,784-org database built for Active Heroes (Shepherdsville, KY). The directory has strong org identification (names, EINs, NTEE codes, financials) but almost no contact information. This milestone fills those gaps so Active Heroes can actually reach out to partner orgs, funders, and peer organizations.

## Core Value

Active Heroes can contact any veteran org in the directory — starting with Kentucky — using real emails, phone numbers, websites, and social media links.

## Requirements

### Validated

- ✓ IRS BMF extraction (80K+ orgs) — existing
- ✓ ProPublica API enrichment (financials per EIN) — existing
- ✓ VA VSO + NRD web scraping — existing
- ✓ Multi-source merge with priority rules — existing
- ✓ 3-tier deduplication (EIN → fuzzy name+city → URL domain) — existing
- ✓ Streamlit dashboard with 6 tabs — existing
- ✓ Active Heroes strategic analysis — existing
- ✓ Checkpoint-based pipeline resumability — existing

### Active

- [ ] Fix NODC extractor (broken URLs)
- [ ] Add Charity Navigator integration (API key signup + extractor config)
- [ ] Add VA Facilities integration (API key signup + extractor config)
- [ ] Stage 7 web enrichment for Kentucky orgs (emails, phones, websites)
- [ ] Social media link capture (Facebook, Twitter, LinkedIn, Instagram)
- [ ] Update Streamlit dashboard to display contact info, social links, and new data fields

### Out of Scope

- Full 80K+ org web enrichment — deferred until Kentucky subset proves the approach (10-20 hr runtime)
- Mobile app — web dashboard is sufficient
- Real-time data sync — batch pipeline is appropriate for this use case
- User accounts or authentication on dashboard — public access is fine

## Context

- **Active Heroes** (EIN 45-4138378) is the primary consumer, based in Shepherdsville, KY
- The existing pipeline (main.py) runs 8 stages; Stages 1-6 and 8 work; Stage 7 (web enrichment) has never been run
- Contact info is critically sparse: 83 phones, 0 emails, 1 website out of 80,784 orgs
- Charity Navigator and VA Facilities extractors exist in code but need free API keys configured in .env
- NODC extractor (nodc.py) is broken — GitHub CSV URLs have changed since initial development
- The enricher.py in transformers/ handles web scraping for social/email but hasn't been exercised at scale
- Dashboard is deployed on Streamlit Community Cloud via GitHub repo vinceRM17/vet-org-directory
- Kentucky subset approach: scrape KY orgs first, validate quality, then expand to other states

## Constraints

- **API Keys**: Charity Navigator and VA Facilities require free API key signups before those extractors work
- **Rate Limiting**: Web enrichment must respect per-source rate limits (0.5 req/sec for enrichment) to avoid IP blocks
- **Runtime**: Even KY subset may take hours depending on org count; checkpointing is essential
- **Tech Stack**: Python 3.9+, Pandas, Streamlit, existing ETL architecture — no stack changes
- **Deployment**: Dashboard updates must stay compatible with Streamlit Community Cloud

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Kentucky-first enrichment | Active Heroes is KY-based; smaller subset validates approach before 80K full run | — Pending |
| Fix existing extractors before adding new data | Broken NODC means missing data; fix foundations first | — Pending |
| API key signup as explicit phase | Can't proceed with Charity Nav / VA Facilities without keys; make it a clear step | — Pending |

---
*Last updated: 2026-02-11 after initialization*

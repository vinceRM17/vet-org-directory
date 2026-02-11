# Requirements: Veteran Org Directory — Data Enrichment

**Defined:** 2026-02-11
**Core Value:** Active Heroes can contact any veteran org in the directory — starting with Kentucky — using real emails, phone numbers, websites, and social media links.

## v1 Requirements

Requirements for this milestone. Each maps to roadmap phases.

### Data Enrichment

- [ ] **ENRICH-01**: Pipeline filters to Kentucky orgs before running web enrichment (reduces scope from 80K to ~2-5K)
- [ ] **ENRICH-02**: Enricher scrapes org websites and extracts email addresses with format validation
- [ ] **ENRICH-03**: Enricher scrapes org websites and extracts phone numbers with format validation
- [ ] **ENRICH-04**: Enricher scrapes org websites and extracts primary website URL
- [ ] **ENRICH-05**: Enrichment runs with checkpoint-based resumability (save progress every 100 orgs)
- [ ] **ENRICH-06**: Enrichment batch processing shows progress bar and estimated time remaining

### Data Quality

- [ ] **QUAL-01**: Extracted emails are validated for proper format and domain existence
- [ ] **QUAL-02**: Extracted phone numbers are validated as 10-digit US numbers
- [ ] **QUAL-03**: Extracted URLs are validated as reachable (HTTP 200)
- [ ] **QUAL-04**: Match rate report generated after enrichment (% of orgs with email, phone, website, social)
- [ ] **QUAL-05**: Confidence score updated to reflect enrichment completeness

### Social Media

- [ ] **SOCIAL-01**: Enricher discovers Facebook page/profile links from org websites
- [ ] **SOCIAL-02**: Enricher discovers Twitter/X handles from org websites
- [ ] **SOCIAL-03**: Enricher discovers LinkedIn page links from org websites
- [ ] **SOCIAL-04**: Enricher discovers Instagram handles from org websites

### Data Sources

- [ ] **SRC-01**: NODC extractor updated with current working URLs
- [ ] **SRC-02**: NODC extractor successfully pulls and merges nonprofit data

### Dashboard

- [ ] **DASH-01**: Dashboard displays email, phone, and website for each org in Explore tab
- [ ] **DASH-02**: Dashboard displays social media links (Facebook, Twitter, LinkedIn, Instagram) for each org
- [ ] **DASH-03**: User can filter orgs by enrichment status (has email, has phone, has website, has social)
- [ ] **DASH-04**: User can export filtered results as CSV with all enriched fields
- [ ] **DASH-05**: Overview tab shows enrichment statistics (% orgs with contact info, by field)

## v2 Requirements

Deferred to future milestone. Tracked but not in current roadmap.

### API Integrations

- **API-01**: Charity Navigator API key signup guide and .env configuration
- **API-02**: Charity Navigator GraphQL extractor pulls ratings and financial data
- **API-03**: VA Facilities API key signup guide and .env configuration
- **API-04**: VA Facilities extractor pulls facility locations and services

### Advanced Enrichment

- **ADV-01**: Waterfall enrichment tries multiple sources sequentially for higher match rates
- **ADV-02**: Confidence scoring per enriched field (0-100%)
- **ADV-03**: Data source attribution shows where each data point originated
- **ADV-04**: Manual review interface for low-confidence records
- **ADV-05**: Enrichment history/audit trail with timestamps

### Scale

- **SCALE-01**: Expand web enrichment beyond Kentucky to all 80K+ orgs
- **SCALE-02**: Automated quarterly refresh to combat data decay
- **SCALE-03**: Async queue system for concurrent enrichment workers

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time enrichment API | Batch processing is sufficient; real-time adds complexity without value for this use case |
| AI-generated contact guessing | Low accuracy, email bounces damage sender reputation |
| Social media auto-posting | Spam risk, brand damage; display handles and let users engage manually |
| Unlimited data source integration | Diminishing returns after 5-7 sources; quality over quantity |
| Mobile app | Web dashboard is sufficient |
| User accounts/auth on dashboard | Public access is appropriate for this directory |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ENRICH-01 | — | Pending |
| ENRICH-02 | — | Pending |
| ENRICH-03 | — | Pending |
| ENRICH-04 | — | Pending |
| ENRICH-05 | — | Pending |
| ENRICH-06 | — | Pending |
| QUAL-01 | — | Pending |
| QUAL-02 | — | Pending |
| QUAL-03 | — | Pending |
| QUAL-04 | — | Pending |
| QUAL-05 | — | Pending |
| SOCIAL-01 | — | Pending |
| SOCIAL-02 | — | Pending |
| SOCIAL-03 | — | Pending |
| SOCIAL-04 | — | Pending |
| SRC-01 | — | Pending |
| SRC-02 | — | Pending |
| DASH-01 | — | Pending |
| DASH-02 | — | Pending |
| DASH-03 | — | Pending |
| DASH-04 | — | Pending |
| DASH-05 | — | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 0
- Unmapped: 22 ⚠️

---
*Requirements defined: 2026-02-11*
*Last updated: 2026-02-11 after initial definition*

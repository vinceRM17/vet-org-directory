# Roadmap: Veteran Org Directory — Data Enrichment

## Overview

This roadmap delivers contact data enrichment for Kentucky veteran organizations, transforming an 80K+ org database with almost no contact info into a usable directory. Phase 1 fixes data sources and establishes Kentucky filtering infrastructure. Phase 2 scrapes websites to extract emails, phones, and social media links. Phase 3 updates the dashboard to display enriched data with validation reports and export capabilities. Each phase builds on the last, starting with infrastructure and ending with user-facing visibility.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation & Kentucky Filtering** - Fix broken extractors and establish Kentucky-first enrichment infrastructure
- [ ] **Phase 2: Contact Enrichment** - Web scraping for emails, phones, websites, and social media with validation
- [ ] **Phase 3: Dashboard & Quality Reporting** - Display enriched data and enrichment quality metrics

## Phase Details

### Phase 1: Foundation & Kentucky Filtering
**Goal**: Pipeline filters to Kentucky orgs and NODC extractor successfully pulls nonprofit data
**Depends on**: Nothing (first phase)
**Requirements**: SRC-01, SRC-02, ENRICH-01, ENRICH-05, ENRICH-06
**Success Criteria** (what must be TRUE):
  1. NODC extractor pulls and merges nonprofit data using working URLs
  2. Pipeline filters to Kentucky orgs before running Stage 7 enrichment
  3. Enrichment runs with checkpoint-based resumability saving progress every 100 orgs
  4. Enrichment shows progress bar and estimated time remaining during batch processing
**Plans**: 2 plans (Wave 1 parallel)

Plans:
- [ ] 01-01-PLAN.md — Fix NODC extractor GitHub URLs (SRC-01, SRC-02)
- [ ] 01-02-PLAN.md — Kentucky filter + enrichment progress bar (ENRICH-01, ENRICH-05, ENRICH-06)

### Phase 2: Contact Enrichment
**Goal**: Kentucky orgs have real contact information scraped from their websites with validation
**Depends on**: Phase 1
**Requirements**: ENRICH-02, ENRICH-03, ENRICH-04, QUAL-01, QUAL-02, QUAL-03, QUAL-04, QUAL-05, SOCIAL-01, SOCIAL-02, SOCIAL-03, SOCIAL-04
**Success Criteria** (what must be TRUE):
  1. Enricher scrapes org websites and extracts emails with format and domain validation
  2. Enricher scrapes org websites and extracts phone numbers with 10-digit US validation
  3. Enricher scrapes org websites and extracts primary website URL validated as reachable
  4. Enricher discovers social media links for Facebook, Twitter, LinkedIn, and Instagram
  5. Match rate report shows percentage of Kentucky orgs with email, phone, website, and social
**Plans**: TBD

Plans:
- [ ] 02-01: TBD during phase planning

### Phase 3: Dashboard & Quality Reporting
**Goal**: Active Heroes can view and export enriched contact data with filtering and quality metrics
**Depends on**: Phase 2
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05
**Success Criteria** (what must be TRUE):
  1. Dashboard displays email, phone, website, and social media links for each org
  2. User can filter orgs by enrichment status (has email, has phone, has website, has social)
  3. User can export filtered results as CSV with all enriched fields
  4. Overview tab shows enrichment statistics as percentages by field type
**Plans**: TBD

Plans:
- [ ] 03-01: TBD during phase planning

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation & Kentucky Filtering | 0/2 | Not started | - |
| 2. Contact Enrichment | 0/TBD | Not started | - |
| 3. Dashboard & Quality Reporting | 0/TBD | Not started | - |

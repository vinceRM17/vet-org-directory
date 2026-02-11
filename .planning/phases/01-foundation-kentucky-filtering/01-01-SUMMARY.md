---
phase: 01-foundation-kentucky-filtering
plan: 01
subsystem: data-pipeline
tags: [nodc, github-api, data-extraction, url-probing]

# Dependency graph
requires:
  - phase: none
    provides: initial project structure
provides:
  - Verified NODC GitHub URLs with master/main branch resilience
  - Enhanced logging for NODC extractor status
  - Graceful handling of missing BMF data files
affects: [02-contact-enrichment, stage-4-pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "URL probing with requests.head() before download"
    - "Branch resilience (master/main variants)"
    - "Clear logging for unavailable data sources"

key-files:
  created: []
  modified:
    - extractors/nodc.py

key-decisions:
  - "NODC BMF repo no longer hosts CSV data (only R build scripts) - documented in code"
  - "Concordance file downloads successfully from verified master branch URL"
  - "Enhanced logging explains which URLs were tried and why extractor returns empty DataFrame"

patterns-established:
  - "Probe URLs with HEAD requests before implementing download logic"
  - "Include both master and main branch variants for GitHub resilience"
  - "Log clear explanations when external data sources are unavailable"

# Metrics
duration: 2min
completed: 2026-02-11
---

# Phase 01 Plan 01: Fix NODC Extractor GitHub URLs Summary

**NODC concordance file downloads successfully (3.3MB); BMF data URLs updated but unavailable (NODC moved to build-your-own-data model)**

## Performance

- **Duration:** 2 minutes
- **Started:** 2026-02-11T21:20:34Z
- **Completed:** 2026-02-11T21:22:39Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- Probed 8 NODC GitHub URLs to verify working endpoints
- Concordance file (concordance.csv) confirmed working at master branch URL
- Updated extractor to include master/main branch variants for resilience
- Enhanced logging to explain attempted URLs and outcomes when no data available
- Verified concordance file downloads successfully (3,352,160 bytes, 23 columns)

## Task Commits

Each task was committed atomically:

1. **Task 1: Probe and fix NODC GitHub URLs** - `f9f9d18` (fix)

## Files Created/Modified
- `extractors/nodc.py` - Updated GitHub URLs with verified working concordance URL, added master/main variants for data URLs, enhanced logging for unavailable data sources

## Decisions Made
- **NODC BMF repo architecture change:** NODC moved from hosting CSV data files to providing R build scripts only. Documented this finding in code comments and log messages.
- **Concordance URL verified:** Master branch URL `https://raw.githubusercontent.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file/master/concordance.csv` confirmed working.
- **Branch resilience pattern:** Added both `master` and `main` branch variants for all URLs to handle GitHub's default branch rename migration.
- **Graceful degradation:** Extractor returns empty DataFrame with clear explanation when BMF data unavailable - no pipeline breakage.

## Deviations from Plan

None - plan executed exactly as written. Plan anticipated that upstream GitHub repos might have removed data files, which proved accurate for BMF data.

## Issues Encountered

**NODC architecture change (expected):** BMF repo (`irs-exempt-org-business-master-file`) no longer hosts CSV data files - only contains R build scripts (`build-master-bmf.R`). This was anticipated by the plan's fallback language. Extractor now logs clear message: "NODC extractor: No data files available. Attempted 6 URLs. As of Feb 2026, NODC BMF repo only contains R build scripts (no hosted CSV data). Returning empty DataFrame."

This is not a blocker - the extractor's fallback logic handles this gracefully. Pipeline Stage 4 will complete without NODC BMF enrichment (mission statements, employee/volunteer counts). Primary data source (IRS BMF) remains intact.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Ready for next plan. NODC extractor:
- Downloads concordance file successfully ✓
- Attempts all known data URLs with resilience ✓
- Returns empty DataFrame gracefully when data unavailable ✓
- Logs clear explanation of attempts and outcomes ✓

No blockers. Pipeline Stage 4 will complete without errors (with empty NODC contribution, as expected given upstream changes).

---
*Phase: 01-foundation-kentucky-filtering*
*Completed: 2026-02-11*

## Self-Check: PASSED

All claims verified:
- ✓ extractors/nodc.py exists and was modified
- ✓ Commit f9f9d18 exists
- ✓ Concordance file downloaded (3,352,160 bytes)

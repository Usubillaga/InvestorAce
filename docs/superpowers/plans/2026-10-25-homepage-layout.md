# Main page organization implementation plan

> **For agentic workers:** Use superpowers:executing-plans for implementation and one fresh final review.

**Goal:** Make the main report navigable without dropping information.
**Architecture:** A presentation-only `dashboard_view.py` wraps the existing
report fragments, supplies CSS/JS, and uses the existing localization pipeline.
**Tech stack:** Python HTML generation, native details, plain browser JavaScript.
**Spec:** `docs/superpowers/specs/2026-10-25-homepage-layout-design.md`

## Global constraints

- Preserve all original information, calculations, assessment data and portfolio privacy.
- Keep English, Spanish and German editions and source-language notices.
- Use existing dependencies; full table is the no-JavaScript fallback.

## Review focus

- Review status must remain visible when advanced columns are hidden.
- Filters retain every original row/cell and do not affect rankings or data.
- Hash links open collapsed ancestors and charts remain usable.
- Original three-language content and encoded portfolio payload survive grouping.
- Mobile page width remains bounded and controls are labelled and keyboard usable.

### Task 1: Reorganize and validate the main report

Files: `dashboard_view.py`, `engine.py`, `i18n_data.py`, `tests/dashboard_browser.cjs`.
Interface: `render(header, table, *, stats, sections)` returns the organized body;
`CSS` and `JS` are presentation-only assets embedded by the existing engine.

- [x] Capture the existing report in all three languages from committed inputs.
- [x] Add the presentation wrapper, search/holdings/reset controls and column toggle.
- [x] Preserve the original fragments in native expandable groups and localize labels.
- [x] Compare before/after content, financial cells, JSON and portfolio payload.
- [x] Run browser interactions, mobile/no-JS and existing assessment-expiry checks.
- [x] Run full tests, review once, address material findings and create an unmerged PR.

### Task 2: Downloadable company analyses

Files: `company_pdf.py`, `company_reports.py`, `test_company_pdf.py`, `engine.py`,
`market_scanner.py`, `scanner.js`, `i18n.py`, `integrity.py`, `weekly_research.py`,
`requirements.txt`. The independent PDF renderer is delegated; root integrates
and validates exports and the main-page changes.

- [x] Render English, German and Spanish PDFs from the exact review packets.
- [x] Publish atomic binary artifacts with distinct universe/market paths.
- [x] Add main-row downloads and three-language scanner links.
- [x] Check dynamic values, missing-data handling, sources/objections and pagination.
- [x] Render and visually inspect representative PDFs and verify real downloads.
- [x] Complete full tests and review PDF integration before the unmerged PR.

## Verification record

- Original baseline:387Python tests passed. Final:400Python tests passed.
- All original main-page text, links,21cells/82rows, assessmentJSON and portfolio payload compared in EN/DE/ES; all preserved. Native/no-JS and mobile checks passed with actual Chart.js4.
- Fresh layout review found localized-sector search and legacy portfolio-reveal regressions; failing browser checks reproduced them, then passed after correction.
- Fresh PDF review found ambiguous native/million units, dropped richer objection responses, and current/archive market-status confusion. Each reproduced by a failing test; all corrected. Captured-rating parity also has a failing-then-passing optional-metric regression.
-696PDF files generated successfully. Real main/scanner downloads match; every language/scope URL returned HTTP200/application-pdf. Seven-page Spanish ZTS output visually reviewed, with no clipping.
- Scope expanded on the user's explicit PDF request. The user retains the merge decision.

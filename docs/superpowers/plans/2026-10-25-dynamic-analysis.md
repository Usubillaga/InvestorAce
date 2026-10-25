# Dynamic Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans; the independent scanner-access task is delegated under dispatching-parallel-agents.

**Goal:** Recompute financial analysis in Python from yfinance without deleting research.
**Architecture:** Versioned fetched facts and pure calculations feed existing engine
rows and scanner evidence; dated primary research remains separate.
**Tech Stack:** Existing yfinance/pandas, Python stdlib and existing static scanner.
**Spec:** `docs/superpowers/specs/2026-10-25-dynamic-analysis-design.md`

## Global Constraints

- Preserve all eight score weights, regime coefficients, historical research and objections.
- No imputed category values, partial-year capitalization or approval by inference.
- No API credentials/client-side financial formulas or changes to actual holdings.
- Model projections disclose assumptions and use the matching cash-flow/rate basis.

## Review Focus

- Quote currency versus financial currency/units, including GBp/GBP.
- Four actual quarters or annual windows; no missing-quarter sums.
- Missing or stale fetches must not remove prior research or masquerade as new facts.
- Reported leveraged cash flow must not be discounted with WACC or lose debt twice.
- Current mechanical results must remain distinct from primary-source approval.

### Task 1: Python data and calculations

Files: `live_analysis.py`, `test_live_analysis.py`, `engine.py`, `evidence.py`.
Interface: `analyze(ticker, symbol, *, quote, risk_free, mrp, as_of)` returns the
spec's snapshot; `refresh_dynamic_analysis()` applies snapshots during run_build.

- [x] Observe failing known-value, freshness, missing-data and preservation tests.
- [x] Implement aligned data extraction and recomputed NGV/DCF/inverse/score inputs.
- [x] Integrate the build, preserve primary values in an archive and retain last-good facts.
- [x] Run targeted tests and a live Zoetis check.

### Task 2: Visible analysis and packet access

Files: `market_scanner.py`, `scanner.js`, `scanner_template.html`,
`tests/scanner_browser.cjs`, dynamic analysis rendering/localization as needed.

- [x] Preserve ZTS research and render current numerical model scenarios beside it.
- [x] Add direct ticker links and obvious packet download (delegated UI scope).
- [x] Verify real downloads and live snapshot rendering on mobile/desktop.
- [x] Run complete tests, review once, fix material findings, create an unmerged PR.

## Verification record

- Known-value, input-sensitivity, unit/period alignment, fallback, preservation, specialty exclusion and score-tolerance regression tests exercised.
- Real yfinance ZTS flow succeeded: TTM to 2026-06-30, quote dated 2026-10-23; three DCF scenarios, NGV and reverse DCF, research and objections retained.
- Complete scanner and focused deep-link/download browser suites passed in Chromium; 14 comparison and 5 assessment-view checks passed.
- Fresh code review identified the original -0.5pp cushion tolerance mismatch; corrected and covered by a failing-then-passing regression.
- Final full Python/lint/workbook results are recorded in the pull request. User retains the merge decision.

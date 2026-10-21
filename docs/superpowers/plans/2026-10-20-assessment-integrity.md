# Assessment integrity implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make model completeness, economic evidence and approved decisions consistent across InvestorAce.
**Architecture:** A pure assessment projection sits beside frozen legacy arithmetic and is archived with each observation. Existing consumers use its eligibility flags; EPV and onboarding receive targeted input repairs.
**Tech Stack:** Python3.11 standard library + existing pandas/yfinance; vanilla JavaScript; GitHub Actions.
**Spec:** docs/superpowers/specs/2026-10-20-assessment-integrity.md

## Global Constraints
- W={g:.15,p:.20,c:.15,b:.15,v:.10,pr:.15,r:.05,d:.05}; no redistribution.
- Golden regime model/hash, historic records and real holdings stay unchanged.
- Missing observations are not zeroes, neutral scores, or automatic sells.
- Financial assumptions and approval are distinct; a source URL alone is not authentication.

## Review Focus
- Old snapshots lack assessment: fallback must remain unreviewed.
- Review inputs change after approval: hashes must invalidate eligibility.
- Quote age, unknown time and future sources withdraw current eligibility.
- Missing balance cells and different fiscal windows must not generate EPV.
- Comparison winner must preserve financial rounds while rejecting an unreviewed model leader.

### Task1 — Reproduce defects and establish baseline
Files: test_assessment_integrity.py, test_epv_integrity.py, test_autoscore_integrity.py.
- [x] Observe clean existing315-test baseline on branch.
- [x] Add regressions for fixed-score verdict, missing-pr/dilution coverage, EPV null debt/scalars/period windows, autoscore missing fundamentals.
- [x] Run CI and record expected failures before production edits.

### Task2 — Central assessment and approval contract
Files: assessment.py, assessment_reviews.json, engine.py, evidence.py.
Interface: assess(row, weights, *, priced_in, raw_score, reviews=None, ticker=None, as_of=None); input_hash(row, weights, priced_in).
- [x] Return all eight contributions, coverage, supported bounds, legacy total and complete-only model score.
- [x] Validate review evidence/timestamps/hash and valuation/normalization contract; preserve null rating otherwise.
- [x] Freeze assessment in observation; gate current verdict, quality screen and new-entry proposal.
- [x] Preserve raw score, raw verdict and raw regime formula replay.
- [x] Pass focused and full tests.

### Task3 — EPV and automatic-input repairs
Files: epv.py, engine.py, autoscore.py, test_epv_integrity.py, test_autoscore_integrity.py.
- [x] Reject invalid scalar EPV inputs and unknown net debt; sanitize statement cells.
- [x] Align common income years before averaging; pair capex/DA in requested window; invalidate old cache schema.
- [x] Preserve missing auto categories; compare only compatible revenue/profit/cash windows.
- [x] Reproduce unchanged Apple workbook fixtures and pass regressions.

### Task4 — Consumer consistency and release
Files: market_scanner.py, stock_compare.py, compare_duel.js, compare.js, framework_view.py, i18n catalogs, README.
- [x] Project frozen assessment in scanner/comparison; mark older snapshots unreviewed.
- [x] Main table shows strict model score and legacy provenance; never present unsupported BUY/SELL approval.
- [x] Reject unreviewed model leader, keep financial points unchanged.
- [x] Check EN/DE/ES and all existing tests/lint/imports/WACC reproduction.
- [ ] Independent code review and verified publication; document remaining financial/methodology gaps.

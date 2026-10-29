# InvestorAce opportunity score implementation plan

> **For agentic workers:** Use superpowers:executing-plans for continuous implementation and one fresh whole-branch review.

**Goal:** Restore actionable automatic labels, business profiles and current-regime suitability for discounted profitable stocks.
**Architecture:** Add a versioned pure decision layer over dated dynamic inputs; retain existing assessment approval and legacy formulas.
**Tech Stack:** Existing Python/yfinance, static HTML/CSS/JavaScript.
**Spec:** docs/superpowers/specs/2026-10-28-opportunity-score-design.md

## Global constraints

- Preserve research, historical scores, sources and objections.
- No ticker-specific recommendation overrides, neutral imputation or price-dependent stale signals.
- Weights: quality 30%, valuation 40%, growth 10%, shareholder/dilution 5%, current macro 15%.
- Strong Buy >=8.5; Buy >=7; Hold Positive >=5.5; Hold Negative >=3.5; otherwise Sell.

## Review focus

- Unknown cash and dividends: robust interval labels without fabricated point scores.
- Cyclical peak earnings: normalized valuation inputs or explicitly missing contributions.
- An open page: expired quotes must withdraw opportunity labels and metrics.
- Old review objections: retain their state without replacing a computed signal with a manual-review badge.
- Desktop/mobile and scanner/PDF: the same methodology and snapshot must travel through each surface.

### Task 1: Pure scoring and financial inputs

Files: opportunity.py, live_analysis.py, test_opportunity.py, test_live_analysis.py.
Interface: assess(row, *, regime, spec, as_of=None) -> versioned opportunity dictionary.

- [x] Write failing behavioral tests for discounted quality, expensive quality, trap caps, regime changes, bounded missing components and stale quotes.
- [x] Implement assessment, profiles and auditable regime/score bounds; add reported and normalized earnings metrics.
- [x] Run targeted unit tests; retain negative evidence.

### Task 2: Shared report/scanner presentation

Files: engine.py, opportunity_view.py, assessment_view.js, market_scanner.py, scanner.js, scanner_template.html, review_packets.py, company_pdf.py, i18n_data.py.
Consumes the opportunity dictionary from Task 1. Produces one visible new score/label, business type, valuation facts, current fit and full regime matrix; preserves old detail views.

- [x] Add a failing integration/expiry test that catches the missing visible signal.
- [x] Integrate frozen opportunity packets, current projections and rendering in report and universe scanner; carry the result to PDF packets.
- [x] Verify desktop/mobile filters, interval rendering, expiry and all three languages.

### Task 3: Verification and publication

Files: README.md and AGENTS.md methodology guidance; existing test workflows.

- [ ] Run full offline Python and JavaScript suites, pyflakes and browser checks.
- [ ] Recalculate the dated universe; inspect ZTS, AR and WKL without assigning preset outcomes.
- [ ] Obtain a fresh code review, resolve material findings, commit and push a PR.
- [ ] Merge/deploy within the user's existing authorization and verify the published generation.

## Review resolutions

- Reproduced and fixed: conditional Buy/Strong Buy gates cap interval endpoints independently, so an attainable Strong Buy is never truncated into a supposedly robust Buy.
- Reproduced and fixed: financial-age expiry uses the same 550-day UTC-date policy in assessment, frozen projection and browser timers.
- Reproduced and fixed: commodity earnings multiples use exactly the cash-cycle years, or remain unknown.
- Price-derived VALUE tags expire with the quote; this is part of signal withdrawal, not a cosmetic classification.
- A provider failure during the local build demonstrated the need to retain a dated cached quote for at most the existing 96 hours. The original timestamp, currency and sanity range are checked; stale/undated/mismatched quotes are rejected.
- Review scope: algorithm, data integrity and product behavior were checked. Predictive returns of heuristic weights and macro coefficients remain unverified; no alpha claim is made.

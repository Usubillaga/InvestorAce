# Observational Timing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Explain current scores and expose experimental trend/extension observations without changing decisions.

**Architecture:** A pure timing module consumes the existing adjusted OHLC pull.
Separate rendering consumes exact score/regime contributions and archived timing
records. Existing paired publication archives the additional source and inputs.

**Tech Stack:** Python, existing pandas/yfinance, unittest, static HTML.

**Spec:** docs/superpowers/specs/2026-10-15-observational-timing.md

## Global Constraints

- No changes to DATA, existing financial formulas, rankings or portfolio rules.
- Observation only; no entry gates, automatic sales or technical score weights.
- Only prior exchange-local dates; 200 valid bars; no fills; explicit missing/stale status.
- SMA(200), SMA-seeded EMA(21), Wilder ATR(14); no new dependencies.
- Never rewrite committed history or index.html for this feature branch.

## Review Focus

- Current/future bars cannot change an earlier observation.
- Missing/invalid history cannot become a negative signal or retain old output.
- Published totals and renormalised scores must not imply invented category data.
- Timing must not change any ranking, decision or portfolio proposal.
- Report and observation must include matching diagnostics and versions.

### Task 1: Pure timing observations and history integration

**Files:** Create `timing.py`, `test_timing.py`; modify `engine.py` history fetch and observation only.

**Interfaces:** `timing.calculate(history, as_of=None) -> dict`,
`timing.unavailable(reason, as_of=None) -> dict`; row key `timing`.

- [ ] Write tests for known SMA/EMA/ATR arithmetic, history length, invalid OHLC,
  zero ATR, staleness, exchange-local cutoff and prefix invariance.
- [ ] Run `python -m unittest test_timing -v`; expect missing timing module failure.
- [ ] Implement the pure calculations; share the existing history pull, reset
  timing on every price fetch and archive timing/version in new observations.
- [ ] Run `python -m unittest test_timing -v`; expect PASS.
- [ ] Commit the task.

### Task 2: Explanations, separate view and invariance verification

**Files:** Create `decision_view.py`, `test_decision_view.py`; modify `engine.py`, `README.md`.

**Interfaces:** `engine.score_components(row) -> dict`; reuse
`engine.regime_fit_components(row)` and `row['timing']`;
`decision_view.panel(rows, explanations, regime) -> str`.

- [ ] Write tests for exact contribution reconciliation including renormalised
  and published-total cases, escaped HTML, missing timing, observation freezing,
  unchanged full-universe decisions/rankings/proposals and full report inclusion.
- [ ] Run `python -m unittest test_decision_view -v`; expect missing API failure.
- [ ] Implement explanations and the collapsed observation view; document methods.
- [ ] Run the focused tests, full unittest suite, pyflakes and workbook reproduction;
  expect all PASS. Compare outputs against the branch base on identical saved inputs.
- [ ] Render desktop/mobile previews from a temporary offline report, then commit.
- [ ] Obtain one fresh whole-branch review, address material findings with regression
  tests, and create a pull request with exact validation and limitations.

## Execution evidence

- Initial baseline: 133 offline tests passed.
- Final suite: 156 offline tests passed; pyflakes, runtime imports and WACC reproduction passed.
- Base-commit comparison: 152 current/archived row cases × 9 decision outputs; zero mismatches; unchanged regime hash.
- Independent review: archived diagnostic versions now also appear in the report, covered by a RED→GREEN regression test.
- Live preview requests were Yahoo-rate-limited; timing remained explicitly unavailable. No performance claim or live strategy activation.
- Desktop/mobile panel layouts inspected; no new page overflow or JavaScript errors. Existing whole-page overflow is unchanged.

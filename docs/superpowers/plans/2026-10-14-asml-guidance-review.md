# ASML Guidance Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox syntax for tracking.

**Goal:** Correct ASML's stale FY2026 guidance proxy and disclose the unresolved FCF normalization.

**Architecture:** Change only the ASML DATA row, preserving numerical FCF and subjective subscores. Existing evidence capture and NORMALIZATION REVIEW rendering carry the new provenance without new framework gates.

**Tech Stack:** Python, unittest, existing report/evidence pipeline, GitHub Actions.

**Spec:** `docs/analysis/ASML-2026-10-14.md` and the user's authorized targeted correction/merge request.

## Global Constraints

- Preserve `fcf=10000`, `shares=383`, subjective categories and all framework coefficients.
- Use EUR millions consistently and include intangible purchases in reported issuer FCF.
- Do not label an undated estimate as a dated reported cash flow or normalized FCFE/FCFF.
- Preserve archived generations and the watchlist; publish only through the existing pipeline.

## Review Focus

- Decimal versus percentage growth: the expected deliver is 36.22184876007506 percentage points.
- Revenue guidance versus cash flow: the reported TTM bridge must not overwrite `fcf`.
- Weighted shares versus outstanding shares: no EPS share count is substituted.
- Dated guidance versus undated FCF: the valuation contract must remain UNVERIFIED.
- Source metadata versus portfolio gates: only Cushion changes in the fixed-input comparison.

### Task 1: Source-backed ASML input and provenance

**Files:** Modify `engine.py` ASML DATA row; create `test_asml_inputs.py`; update the analysis note.

**Interfaces:** Consumes `engine.DATA`, `evidence.current_build()`, `observation()`, `build_html()`, score/regime/portfolio functions. Produces the corrected ASML row and its frozen evidence.

- [x] Write tests for primary-guidance arithmetic, the complete issuer FCF bridge, unverified estimate status, bootstrap preservation, isolated decisions and evidence/render visibility.
- [x] Run `python -m unittest test_asml_inputs -v`; five new expectations failed for stale deliver and missing source/review metadata.
- [x] Correct ASML deliver and attach dated guidance, reported-cash-flow review metadata and the existing review badge/note.
- [x] Run targeted tests and full `python -m unittest discover -p 'test_*.py' -q`; 109 tests pass.
- [x] Verify the current generation; recompute all names with fixed archived quotes/rates and the ASML overlay, then validate and render a new isolated report generation using the existing functions.
- [x] Append concrete results to the analysis note; review the complete diff and commit.
- [ ] Obtain the fresh whole-branch review, create/merge the PR, verify CI/deployment and update the existing watchlist cursor without replacing concurrent progress.

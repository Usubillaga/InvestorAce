# Research Review Packets Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Make scanner candidates ready for an auditable three-role review using
one frozen evidence packet and explain the scanner's operating state.

**Architecture:** A dependency-free packet builder consumes frozen inputs and
existing scanner projections. The static scanner embeds packets and downloads the
chosen packet without invoking models or changing ratings.

**Tech Stack:** Python standard library, existing scanner JavaScript, Playwright.

**Spec:** `docs/superpowers/specs/2026-10-25-research-review-packets-design.md`

## Global Constraints

- Keep all eight score weights, NGV/DCF calculations and regime formulas unchanged.
- Keep `NOT_STARTED`/`NOT_RUN` explicit; a packet cannot grant approval.
- Preserve nulls and unresolved objections; no live network calls in page builds.
- Separate universe and market identity; no new recurring API cost.
- Prepare an unmerged PR; preserve current main and existing histories.

## Review Focus

- Same ticker in both lists must retain its distinct inputs and methodology.
- A corrected objection remains unresolved without separate evidence verification.
- Later browser exports must disclose the frozen cutoff and avoid claiming freshness.
- Missing/invalid sources and script-like text must remain data, never executable.
- A held-open panel must not download another ticker after changing filters/tabs.

### Task 1: Frozen packets and scanner data

**Files:** Create `review_packets.py`, `test_review_packets.py`; modify `market_scanner.py`.
**Interfaces:** `build_packet(*, scope, ticker, origin, inputs, output, sources,
issues, objections, research) -> dict`; attach separate maps to scanner JSON.

- [x] Write failing integration tests for the spec's snapshot and identity behavior.
- [x] Observe the expected missing-packet failures.
- [x] Implement pure packet creation with identical hashes for the three roles.
- [x] Test changed inputs/sources/objections, nulls and non-mutation.
- [x] Run focused and full Python tests; commit this task.

### Task 2: Per-stock downloads and operating status

**Files:** Modify `scanner.js`, `scanner_template.html`, `tests/scanner_browser.cjs`;
create `docs/analysis/SCANNER-REVIEW-2026-10-25.md`.
**Interfaces:** Consume Task 1's separate maps and download the original JSON text
verbatim; retain frozen `as_of`. Do not serialize financial numbers in JavaScript.

- [x] Add browser assertions for both lists' downloads, nulls and unchanged ratings.
- [x] Observe failures before adding the download control.
- [x] Add per-stock download and distinct scanner/rating status text.
- [x] Run scanner browser checks at desktop/mobile and all Python/Node/lint checks.
- [x] Record the live scanner audit and final validation; commit and review the branch.

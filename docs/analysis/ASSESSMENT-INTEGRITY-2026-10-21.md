# Assessment integrity repair ledger — 21 October 2026

Plan: `docs/superpowers/plans/2026-10-20-assessment-integrity.md`.
Spec: `docs/superpowers/specs/2026-10-20-assessment-integrity.md`.

Initial source base8521596; current-main8b50322 incorporated locally, preserving
AMD, Realty Income, daily briefing and generated history. No archived history
or actual holding is edited by the repair.

## Reproduced defects

The315 existing offline tests passed after installing the declared dependencies.
The first22 new regression cases exposed35 failures (including scalar subcases)
and one nonfinite-JSON error. Later focused regressions reproduced unreviewed
comparison leaders, quote/time mismatch, expired price contribution, an implicit
quality threshold in regime research, and approval despite an open objection.
Each case was observed failing before its correction.

## Implemented corrections

- Versioned strict assessment keeps all eight original weights and unknown values.
  Complete model arithmetic, raw legacy values and explicit analyst approval are
  separate. Quote expiry withdraws the price-dependent contribution.
- Input-bound approvals require dated evidence, reviewer and expiry; financial,
  score, rate, quote or objection changes invalidate the reviewed packet. Existing
  material objections are frozen from scanner_notes and cannot be closed merely
  by changing their state to corrected. A register URL does not authenticate data.
- Main report, scanner and comparison share the frozen assessment. Old snapshots
  cannot acquire approval through publication. Raw score and legacy_verdict remain
  reproducible for historical evidence; current decisions require the new gate.
- New-entry proposal slots require reviewed eligibility. Existing holdings and
  stops are unchanged. Quality-rank criticism is withheld without comparable
  reviewed scores. Pure regime formulas and their golden hash stay unchanged.
- EPV requires a known net-debt bridge, positive shares/rate, finite inputs and
  aligned income windows. Known zero/net cash and the Apple fixtures remain valid.
  Cache version2 rejects earlier fabricated-zero inputs and discloses assumptions.
- Automatic drafts retain missing components, avoid TTM/prior-annual comparisons,
  partial-quarter margins and guessed dividend-yield units. They remain drafts.

## Rulings and remaining limits

Ruling: preserve raw score/risk/valuation functions for historical replay and add
the strict contract beside them, instead of rewriting frozen observations. Cost
if misunderstood: callers of raw APIs can still misuse legacy estimates; those
APIs and the archived score field are now expressly documented as legacy.

Ruling: use the synthetic approval fixtures only to test the gate. Do not insert
live approvals for existing issuers merely because tests pass. Cost: current
approved-entry capacity can remain empty pending actual financial review; that
does not imply low business quality or a sell instruction.

Ruling: keep score weights, regime curves and existing DCF case calculations.
Sector-specific calibration, currency-consistent risk-free curves, FCFF/FCFE
migration, and validation of overlapping valuation signals require separate
evidence. Cost: legacy valuation scenarios retain their disclosed limitations.

Verification: focused Python/JavaScript tests,315-test baseline,340-test interim
suite, lint/import checks and unchanged WACC demonstration were observed.
Final expanded suite, independent review and publication are recorded in the PR.

## Final independent review and author correction pass

The independent whole-branch code review found no critical defects and requested
four important corrections. These were fixed in one author pass:

1. Annual revenue could still be combined with quarterly TTM operating income
   or cash flow. New regressions reproduced false profitability/cash scores and
   mismatched quarter endpoints. Draft inputs now retain sorted fiscal windows;
   margins require identical windows and net-debt/EBITDA matching endpoints.
2. New material scanner objections could coexist with a frozen approved rating.
   Central projection now accepts current objections; scanner and comparison
   withdraw approval while retaining the original packet separately. A regression
   verifies both consumers and proves the archived assessment is unchanged.
3. Seven-day entry plans could outlive a one-day review. Proposal plans now inherit
   the frozen assessment cutoff and the earlier of approval/quote/policy expiry.
   Post-expiry fills are rejected; date-only fills on an intraday boundary are
   ambiguous and require an aware timestamp. Existing position stops never reset.
4. Static browser displays could retain approvals after expiry. Shared versioned
   browser projection now updates on load, exact expiry timers, tab visibility and
   page restoration. Main, scanner and comparison withdraw expired ratings and
   entry levels; stale quotes also remove priced-in contributions. Portfolio rank
   diagnostics are withheld after comparable holding approvals lapse, including
   when the portfolio panel is opened later.

The minor scanner status/counter finding is folded into correction4: displaying
an approved row as unreviewed and hiding open objections affects the same visible
approval contract. Reviewed/pending/open-objection labels and the material-objection
counter now use that contract. Browser checks exercise both reviewed and open rows.

An additional author finding is corrected: a hash-bound approval cannot predate
its quote or financial/share source. Full timestamps retain their precision;
malformed and timezone-free timestamps are rejected instead of truncating to a
calendar date. Actual date-only sources retain their disclosed date precision.

Evidence: six new Python regression cases first produced eight failures and one
missing-context API error. The former comparison renderer was replayed in Chromium
and retained approval past expiry; the fixed renderer passes the same assertion.
Final validation:348 Python tests,19 Node tests, lint, runtime imports and diff
checks pass. Five generated browser pages (main EN/DE/ES, scanner, comparison)
pass simulated approval and quote expiry, including timers crossing the exact
deadline without reload. EN/DE/ES translation inventory has no gaps. The WACC
workbook demonstration retains its pre-existing rounding differences.

These are software/contract checks, not primary-source certification of every
issuer, an investment-committee approval, or evidence of investment performance.

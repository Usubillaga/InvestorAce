# Devon and Zoetis source update

**Goal:** Carry the user's October 23 research into InvestorAce and prepare a PR for the user to merge.

**Architecture:** Update the two existing DATA rows, source register and scanner notes. A small opt-in bootstrap guard preserves deliberately unresolved primary-review inputs. Existing report/evidence paths publish the review; historical generations remain immutable.

**Constraints:** Preserve framework weights, regime formulas, portfolio rules and legacy subjective scores. Reported quarterly/half-year FCF and conditional DCF assumptions must never become verified annual normalized cash. No new rating or analyst approval.

**Review focus:** DVN post-merger shares versus EPS weighted shares; mixed acquisition perimeter; FCFF/equity bridge; Eagle Ford proceeds and lost cash flow. ZTS retrospective reporting-lag recast, half-year versus annual cash and debt-funded returns. Bootstrap must preserve both incomplete and completed opt-in primary packets while ordinary Yahoo draft and producer paths still work.

## Task 1: Primary evidence, update protection and disclosures

Files: `engine.py`, `i18n_data.py`, `source_reviews.json`, `scanner_notes.json`, `test_devon_zoetis_inputs.py`, `docs/analysis/DVN-ZTS-2026-10-23.md`.

Interfaces: DATA → bootstrap → observation/assessment → existing report/scanner. Source register and notes provide source facts, conditional values and material unresolved objections without approving categories.

- [x] Run baseline offline suite with installed project dependencies.
- [x] Add a failing regression for primary-review packets being overwritten by Yahoo, including the mid-cycle path. Expected: new guard tests fail before the fix.
- [x] Correct dated reported inputs; preserve missing annual normalization; add source-backed review and comparison notes with null approved outputs.
- [x] Implement the opt-in guard before the producer branch. Expected: primary-review packets survive, ordinary draft paths remain functional.
- [x] Run targeted and full offline suites, lint, JavaScript contracts and WACC reproduction. Render an isolated report with dated reference quotes and inspect both disclosures. Expected: all required checks pass; no rating/new entry, no normalized NGV and no cash-flow cushion for either company.
- [ ] Obtain one fresh whole-branch review, address material findings, commit and open a PR. Do not merge or rewrite generated history.

## Progress

- Initial baseline could not import missing yfinance; installed the declared dependencies and reran. No code changes were made to accommodate the environment.

- Baseline: 348 tests passed (89.779s). RED: five failures and one missing-data error reproduced the unsupported inputs and bootstrap overwrite; ordinary refresh passed. GREEN: all six targeted tests passed.
- Only DATA rows DVN/ZTS changed; all prior source/notes entries compare equal to main. Regime golden-master errors: none. Lint and 19 JavaScript contract tests passed; WACC workbook reproduced.
- Isolated report render: 61,719 bytes; DVN 85% category coverage and ZTS 5%, both incomplete with null current model score/rating and no new-entry eligibility. Base DCF and equity perpetuity reproduced independently from the stored assumptions.
- A verbose full-suite run ended before its summary without a traceback. Its last test passes in isolation; rerunning the full quiet suite to establish a complete result before commit.
- The complete quiet run finished 354 tests with one existing inventory failure for the new `primary-review` UI label. Added the missing German/Spanish catalog entries; no financial/behavioral assertion failed.

- Independent whole-branch review: no critical/important findings; declined-to-judge list empty.
- Final: minor (deferred): ZTS financial debt 9,048 and net debt 7,375 are carrying-value figures; principal debt would be 9,150 and principal-based net debt 7,477. Labeling that basis more explicitly is a nonblocking future clarity improvement; no current valuation uses it.
- Translation inventory plus all six new regression tests pass after adding the label (7 tests); full suite rerun pending.

- Final complete run: 354 Python tests passed (101.617s); 19 JavaScript tests passed. Lint and diff whitespace checks passed. Fresh whole-branch review found no blocking issue.
- Code and reviewed evidence are ready for the user-controlled PR/merge workflow; no production deployment is performed by this task.

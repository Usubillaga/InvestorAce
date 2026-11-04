# OXY valuation input integrity correction

The user requested a working correction: OXY must not retain Buy while known monetary input errors remain unresolved.

Root cause: source_reviews.json records two material input conflicts only in prose: the cycle cash/earnings averages span the disposed OxyChem business, and the common-equity cash flow omits Berkshire preferred claims. Dynamic refresh ignores both and regenerates Buy (7.8904), NGV91.3028 and DCF114.9828 from the same disputed inputs.

Implement typed, dated input_conflicts in the valuation source record. These are concrete input defects, distinct from generic PARTIAL/REVIEW_REQUIRED. Propagate active conflicts into every fresh/cached calculation. Withdraw affected valuation cash flow, earnings multiple, NGV, DCF and reverse DCF rather than inventing normalized figures or a Hold score. Preserve reported financials, quality components, sector profiles, raw regime formula, historical generations and analyst objections. Show Valuation blocked with its reasons, and no Buy price. Removing a conflict requires a separately reviewed continuing-operations/common-equity bridge; this fix does not claim that work is complete.

No ticker-specific label override; only OXY receives the documented conflict entries. Other pending-review names retain automatic signals. Additive packet fields; opportunity-v18.1 records the behavior change; clients retain support for previous frozen schemas.

Implementation / verification
- [x] Regression tests first: actual frozen OXY facts, direct and cached/fresh refresh, no Buy/NGV/DCF, missing-data honesty and clean-row control; malformed/future conflict rejection.
- [x] Source-register validation and propagation; valuation calculation/price scan consume the input barrier; EN/DE/ES expose it.
- [x] All Python/Node contracts, lint and frozen universe before/after replay. Fresh code review. PR and normal deployment after successful checks.

Baseline: 539 Python tests passed after installing existing repository dependencies. The initial dependency-free run failed because yfinance was absent; no product regression was inferred.

Review: fresh read-only reviewer found a browser cached-breakdown bypass. Added a failing Node reproduction, then cleared disputed components/old exact fits and DOM tables while preserving newly calculated bounded fits. Seven Node opportunity contracts and six new Python regressions pass. The full-suite version pins were intentionally advanced to opportunity-v18.1; weights themselves are unchanged.

Frozen replay: 85 tickers at the 2026-11-04 captured market/macro inputs, only OXY numerical outputs changed. OXY Buy7.8904 becomes BLOCKED_INPUTS with no composite or purchase price. Reported FCF4,793m and financial quality8.1556 remain visible; all five regime bounds remain available. Full scoreboard HTML rendered successfully offline with Valuation blocked and both reasons. Historical records were not edited.

Final verification: 545 Python tests pass; 26 Node checks pass (14 comparison, 5 assessment, 7 opportunity). Pyflakes, whitespace checks and WACC workbook reproduction pass. Independent review P2 addressed with RED-to-GREEN browser regression. No outstanding code-review blockers. The issuer economic normalization and reviewed analyst score remain deliberately open, visibly separate from repaired software enforcement.

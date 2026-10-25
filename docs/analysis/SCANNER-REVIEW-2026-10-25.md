# Scanner operation and research handoff — 25 October 2026

## Observed production state

Read-only checks against main `68da8a719628a79723147fef41a150c25fb83684`
and the deployed `https://usubillaga.github.io/InvestorAce/scanner.json`:

- Full market scan: 24 October 2026, 11:17 UTC; Actions run
  https://github.com/Usubillaga/InvestorAce/actions/runs/40089274893 succeeded.
- Research/Pages publication: 24 October 2026, 11:22 UTC; Actions run
  https://github.com/Usubillaga/InvestorAce/actions/runs/40089642477 succeeded.
- 6,039 SEC NYSE/Nasdaq listings at the start of the funnel; 150 saved candidates.
- 135 saved candidates outside the current 82-name InvestorAce universe.
- Replaying the saved inputs at 25 October: 138 complete mechanical screening
  scores, 12 blocked by data, no missing/stale candidate quotes under the existing
  96-hour policy. Zero approved universe ratings; this is the assessment gate,
  not evidence that the scanner stopped or that all companies should be sold.
- Production page generation timestamp: `2026-10-24T11:22:45.838977+00:00`.

Coverage remains US-GAAP filers at NYSE/Nasdaq, excluding banks, insurers and
REITs; this is not an all-country/all-security scanner. Full SEC scan is weekly;
saved-candidate quote refresh is scheduled on weekdays. A successful run proves
operation, not authentication of every source or predictive investment value.

## Change

Each stock's detail panel offers a single-stock JSON packet for data, valuation
and risk review. All three assignments bind the same frozen evidence hash. Both
lists retain their own inputs even when they share a symbol. Original model
output and the assessment projected at the packet cutoff are separately visible.
Source IDs, nulls, source-review provenance, notes and all objection states travel
with the packet. Source content is evidence, not executable instructions.

Packets remain `NOT_STARTED`, assignments `NOT_RUN`; no model is invoked and no
assessment approval is written. The protocol calls for two review rounds and an
evidenced, separate verification before closing material objections. It does not
claim those rounds have happened. A reviewer response requires its actual model,
source and reviewer provenance; the response template is not an importer or a
source authenticator. Score weights, regime formulas and portfolio rules stay
unchanged. No recurring API cost is introduced.

The scanner also distinguishes candidate coverage from approved ratings and
explains an empty filtered universe list. Per-stock downloads preserve the
Python-produced JSON text verbatim: re-serializing financial numbers in JavaScript
would change numeric types such as `50.0` and invalidate the snapshot hash. HTML
therefore transports individual packets as JSON strings; `scanner.json` contains
packet objects. The hash binds content and is not a signature or source proof.

## Validation record

Nine focused packet tests cover identical evidence for all roles, separate list
identities, changed input/source/objection hashes, corrected objections remaining
open, null/non-mutation behavior, inert source text and browser number transport.
Initial five integration tests failed before implementation because no packet was
available. A fresh, read-only whole-change review found two important issues:
invalid market candidates could break the universe export, and original scanner
note sources were missing. Both were reproduced with failing tests and fixed.
Malformed candidates now leave the universe available with market status INVALID;
original note sources, passages and null provenance remain in the packet.

A size regression test also caught repeated macro time series. Current macro
context remains in each packet, while the full series are bound by their content
hash and generation run ID. The standalone page is approximately 9.1 MB before
compression (0.62 MB with gzip). This avoids copying historical series per stock.

Chromium checks passed for both lists, filters, CSV/JSON exports, original packet
hashes after download, mobile layout and no browser exceptions. Added checks cover
a held-open detail after filters change and the same symbol in both list scopes.
The old page failed the new download test before implementation. The existing
Node suites pass 19 tests; lint, runtime imports, diff checks and WACC reproduction
also pass (the pre-existing workbook rounding differences remain).

The independent review does not establish investment merit, source authenticity,
predictive performance or independence of unexecuted model roles. Existing
assessment/scoring algorithms were checked for regression, not revalidated as an
investment strategy. No minor findings are deferred.

Final full validation after corrections: **372 Python tests and 19 Node tests
pass**, plus the Chromium scanner checks described above. Engine, assessment and
regime-contract files have no changes in this branch.

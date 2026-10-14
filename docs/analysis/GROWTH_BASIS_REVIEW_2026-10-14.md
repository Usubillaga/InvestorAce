# Explicit growth basis and reviewed ticker publication

Revenue, bookings, earnings and production growth previously flowed into
`deliver - 100 * implied_growth` as though they were cash-flow growth. A
negative result could deduct priced-in points, add 0.6 risk and override the
verdict. This change permits that comparison only when the row explicitly
declares `deliver_basis='CASH_FLOW'`. Missing and unknown types are not
comparable. The mid-cycle exclusion and -0.5pp tolerance are retained.

Existing labels are typed without changing financial numbers or components.
ENB's DCF/share CAGR remains a cash-flow metric; ambiguous PFE guidance stays
untyped. This is metric classification, not verification of the underlying
source or its suitability as a forecast. Main-table badges explain withdrawn
cushions and existing unverified valuation contracts. Observation diagnostics
include the growth contract and version `explicit-cash-flow-growth-v1`.

NFLX's 11,152m FCF, 4,163.94m shares, 24% revenue proxy and components are
retained. The row is marked `REVIEW_REQUIRED`, with its missing primary-source
bridge, financial period, publication date and share-count date stated. The
fix does not certify those inputs or substitute invented financial evidence.

## Controlled model comparison

Base: `142ac843e628dd79fc71eea4bfc265ff00bb64fb`.
Inputs: all 76 rows from the immutable generation
`20261014T014342186957-2301140aa7724db7bc270bf7ffc3690c`.
The old source replay matched the saved NGV, cover, cushion, score, risk and
regime outputs. The new run changed only metric typing and review metadata;
prices, rates, cash flows, shares, components and positions were frozen.
No external data was fetched.

| Ticker | Score before → after | Risk before → after | Verdict before → after |
|---|---:|---:|---|
| LULU | 6.40 → 6.70 | 2.7 → 2.1 | DO NOT ADD → ACCUMULATE |
| PFE | 5.85 → 6.15 | 4.1 → 3.5 | DO NOT ADD → HOLD |
| TSLA | 4.45 → 4.525 | 4.3 → 3.7 | DO NOT ADD → AVOID |

These are consequences of withdrawing invalid proxy penalties, not improved
financial evidence. No other row's score, risk or verdict changed. The score
ordering moved LULU from 28 to 20 and PFE from 37 to 34 in this frozen run.
The 15-name quality and Reflation screens were identical. The duration screen
admitted PFE and LULU, displacing CVX and PEP through its existing verdict
eligibility filter; its cover-only ordering rule was unchanged.

NGV, cover, reverse-DCF implied growth and all five regime fits were identical
for every row. Every regime book retained the same 30 names and order. All
five portfolio proposals, including their entry plans, were identical.
NFLX's cushion changed from +15.732pp to unavailable; its NGV 21.628235,
score 7.00, risk 2.1 and fits were unchanged under these controlled inputs.

## Publication path

`add-ticker.yml` now drafts inputs, lints, imports real modules, runs the full
offline suite and validates the candidate before pushing. It stages only
`engine.py` on a new run-specific branch, opens a draft PR and explicitly
dispatches `test.yml`. It does not render or commit a report, history archive
or current pointer, and does not update main. Existing-ticker no-ops create
no branch or PR. Issue responses describe the draft rather than claiming a
publication. Relevant Python, dependency, fixture and workflow changes on
main now trigger the normal tested paired-generation deployment.

Repository settings still need to permit Actions to create PRs. A main-branch
ruleset requiring PRs and the `test` check remains an administrator action;
these workflow changes cannot enforce that policy for every repository writer.

## Validation executed

- New basis/penalty/HTML/autoscore tests failed before the production fix and
  passed afterward. The final full offline suite contains 116 passing tests.
- The 5,000-case frozen oracle still checks identical cash-flow arithmetic,
  score, risk, verdict and fit for explicitly typed cash-flow inputs. A separate
  legacy test permits only withdrawal of untyped growth penalties. Neither
  the frozen source fixture nor regime golden-master expectations changed.
- `FrozenGrowthReplay` pins the three score/risk/verdict changes above and
  unchanged valuations and all five 30-name regime books using saved inputs.
- Pyflakes, runtime imports, structural validation and `git diff --check`
  pass. `actionlint` 1.7.12 accepts the three changed workflows.
- The actual candidate-commit shell step was executed against a temporary
  local Git remote. A no-op created no branch; a changed candidate committed
  only `engine.py` on its new branch, preserving main and the last report even
  when an unstaged report modification was present.
- Existing atomic-publication, failure-preservation, hash-tampering, shared
  macro and language-archive tests remain in the full suite. Historical
  reports, observations, archives and `_current` were not modified.

Run the durable regression checks with:

```console
python -m unittest test_growth_basis test_evidence_framework.LegacyEquivalence -v
python -m unittest discover -p 'test_*.py' -v
```
